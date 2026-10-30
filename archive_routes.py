"""Study archive — DB + files + dictionary in one ZIP."""
import io, os, sqlite3, zipfile, json, secrets
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import (render_template, request, send_file, abort, g, flash,
                   redirect, url_for)
from database import query, one
from config import DB_PATH, UPLOAD_DIR
from export import csv_bytes, xlsx_bytes, pdf_bytes


def register(app):
    def role_required(*roles):
        def deco(fn):
            @wraps(fn)
            def wrapper(*a, **kw):
                if not g.user or g.user["role"] not in roles:
                    abort(403)
                return fn(*a, **kw)
            return wrapper
        return deco

    @app.route("/study/<int:sid>/archive")
    @role_required("ADMIN", "RESEARCHER")
    def study_archive_page(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        studies = query("SELECT id, study_code, title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("study_archive.html", s=s, studies=studies)

    @app.route("/study/<int:sid>/archive/download")
    @role_required("ADMIN", "RESEARCHER")
    def study_archive_download(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        include = request.args.get("include", "db,dictionary,values,specimens,uploads")
        include = set(include.split(","))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            # ── README ──
            readme = f"""Research Study Archive
======================
Study      : {s['study_code']} — {s['title']}
Exported   : {stamp}
Exported by: {g.user['username']}

Contents
--------
"""
            if "db" in include:
                readme += "  database/research.db  — full SQLite snapshot\n"
            if "dictionary" in include:
                readme += "  data_dictionary.csv   — parameter spec\n"
            if "values" in include:
                readme += "  study_values.csv      — parameter values for this study\n"
                readme += "  participants.csv      — participant roster\n"
            if "specimens" in include:
                readme += "  biospecimens.csv      — sample tracking\n"
            if "uploads" in include:
                readme += "  uploads/              — participant attachments (if any)\n"
            readme += "\nStudy metadata:\n"
            for k in ("id","study_code","title","pi","institution","department",
                      "protocol_no","ethics_no","start_date","end_date","status",
                      "sample_target","frozen","cutoff_date"):
                if s[k] is not None:
                    readme += f"  {k:15s} = {s[k]}\n"

            z.writestr("README.txt", readme)

            # ── DB snapshot (this study only, but self-contained) ──
            if "db" in include:
                snapshot = Path(str(DB_PATH) + f".snap_{secrets.token_hex(4)}")
                try:
                    src = sqlite3.connect(DB_PATH)
                    dst = sqlite3.connect(str(snapshot))
                    src.backup(dst); dst.close(); src.close()
                    z.write(str(snapshot), "database/research.db")
                finally:
                    try: snapshot.unlink()
                    except Exception: pass

            # ── Data dictionary ──
            if "dictionary" in include:
                params = query("""SELECT p.*, g.name AS group_name FROM parameters p
                                  LEFT JOIN parameter_groups g ON g.id=p.group_id
                                  WHERE p.active=1 ORDER BY p.category, p.sort_order, p.name""")
                headers = ["Code","Name","Category","Group","Type","Unit",
                           "Ref low","Ref high","Ref text","Choices","Required"]
                rows = [[p["code"],p["name"],p["category"] or "",p["group_name"] or "",
                         p["data_type"] or "",p["unit"] or "",
                         p["ref_low"] if p["ref_low"] is not None else "",
                         p["ref_high"] if p["ref_high"] is not None else "",
                         p["ref_text"] or "",p["choices"] or "",
                         "Yes" if p["required"] else "No"] for p in params]
                z.writestr("data_dictionary.csv", csv_bytes(headers, rows))

            # ── Participants roster ──
            if "values" in include:
                parts = query("""SELECT * FROM participants
                                 WHERE study_id=? AND archived=0
                                 ORDER BY participant_code""", (sid,))
                headers = ["Participant code","Classification","Group","Consent",
                           "Visit date","Sex","Age","Screening","Enrollment","Notes"]
                rows = [[p["participant_code"], p["classification"] or "Undetermined",
                         p["group_type"], p["consent_status"], p["visit_date"] or "",
                         p["sex"] or "", p["age"] or "",
                         p["screening_status"], p["enrollment_status"],
                         p["notes"] or ""] for p in parts]
                z.writestr("participants.csv", csv_bytes(headers, rows))

                # Values
                vals = query("""SELECT p.participant_code, r.visit_date,
                                       pa.code AS pcode, pa.name AS pname,
                                       pa.unit, v.numeric_value, v.value_text,
                                       v.value_state, pa.category
                                FROM participant_values v
                                JOIN participant_records r ON r.id=v.record_id
                                JOIN participants p ON p.id=r.participant_id
                                JOIN parameters pa ON pa.id=v.parameter_id
                                WHERE p.study_id=?
                                ORDER BY p.participant_code, pa.sort_order""", (sid,))
                headers = ["Participant","Visit date","Category","Parameter code",
                           "Parameter","Unit","Numeric value","Text value","State"]
                rows = [[v["participant_code"], v["visit_date"] or "",
                         v["category"] or "", v["pcode"], v["pname"],
                         v["unit"] or "",
                         v["numeric_value"] if v["numeric_value"] is not None else "",
                         v["value_text"] or "", v["value_state"]] for v in vals]
                z.writestr("study_values.csv", csv_bytes(headers, rows))

            # ── Biospecimens ──
            if "specimens" in include:
                specs = query("""SELECT b.*, p.participant_code FROM biospecimens b
                                 JOIN participants p ON p.id=b.participant_id
                                 WHERE p.study_id=? ORDER BY b.id""", (sid,))
                headers = ["Participant","Sample ID","Type","Collection date",
                           "Storage location","Freeze-thaw count","Volume","Notes"]
                rows = [[b["participant_code"], b["sample_id"], b["sample_type"] or "",
                         b["collection_date"] or "", b["storage_location"] or "",
                         b["freeze_thaw"] or 0, b["volume"] or "",
                         b["notes"] or ""] for b in specs]
                z.writestr("biospecimens.csv", csv_bytes(headers, rows))

            # ── Uploads ──
            if "uploads" in include:
                parts = query("""SELECT id FROM participants WHERE study_id=?""", (sid,))
                for p in parts:
                    folder = Path(UPLOAD_DIR) / "participants" / str(p["id"])
                    if not folder.exists(): continue
                    for f in folder.iterdir():
                        if f.is_file():
                            z.write(str(f),
                                    f"uploads/participant_{p['id']}/{f.name}")

        buf.seek(0)
        name = f"{s['study_code']}_archive_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        try:
            from database import execute
            execute("""INSERT INTO audit_log (user_id, action, target_type, details)
                       VALUES(?, 'ARCHIVE_STUDY', 'study', ?)""",
                    (g.user["id"], f"{sid}:{name}"))
        except Exception: pass
        return send_file(buf, download_name=name, as_attachment=True,
                         mimetype="application/zip")
