"""Bulk operations on participants."""
import io, csv
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, send_file)
from database import query, one, execute
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

    def audit(action, tid="", details=""):
        try:
            execute("""INSERT INTO audit_log
                       (user_id,action,target_type,target_id,details,ip)
                       VALUES(?,?,?,?,?,?)""",
                    (g.user["id"], action, "participant", str(tid),
                     details, request.remote_addr or ""))
        except Exception:
            pass

    @app.post("/participants/bulk-action")
    @role_required("ADMIN", "RESEARCHER")
    def participants_bulk_action():
        ids = request.form.getlist("pid")
        action = request.form.get("action", "")
        if not ids:
            flash("Select at least one participant.", "warning")
            return redirect(url_for("participants_list"))

        try:
            ids_int = [int(x) for x in ids]
        except ValueError:
            flash("Invalid selection.", "danger")
            return redirect(url_for("participants_list"))

        if action == "classify":
            cls = request.form.get("classification", "Undetermined")
            if cls not in ("Control", "Study", "Excluded", "Undetermined"):
                abort(400)
            for pid in ids_int:
                execute("""UPDATE participants SET classification=?,
                           classification_reason='bulk',
                           classified_at=CURRENT_TIMESTAMP WHERE id=?""",
                        (cls, pid))
            audit("BULK_CLASSIFY", ",".join(map(str, ids_int)), cls)
            flash(f"Classified {len(ids_int)} participant(s) as {cls}.", "success")

        elif action == "group":
            grp = request.form.get("group_type", "Unclassified")
            for pid in ids_int:
                execute("UPDATE participants SET group_type=? WHERE id=?", (grp, pid))
            audit("BULK_GROUP", ",".join(map(str, ids_int)), grp)
            flash(f"Set group '{grp}' for {len(ids_int)} participant(s).", "success")

        elif action == "archive":
            for pid in ids_int:
                execute("UPDATE participants SET archived=1 WHERE id=?", (pid,))
            audit("BULK_ARCHIVE", ",".join(map(str, ids_int)))
            flash(f"Archived {len(ids_int)} participant(s).", "success")

        elif action == "reclassify":
            try:
                from criteria_engine import classify_participant
                for pid in ids_int:
                    cls, reason, _ = classify_participant(pid)
                    execute("""UPDATE participants SET classification=?,
                               classification_reason=?, classified_at=CURRENT_TIMESTAMP
                               WHERE id=?""", (cls, reason, pid))
                audit("BULK_RECLASSIFY", ",".join(map(str, ids_int)))
                flash(f"Re-evaluated {len(ids_int)} participant(s).", "success")
            except Exception as e:
                flash(f"Reclassify failed: {e}", "danger")

        elif action == "export":
            headers = ["Study", "Participant", "Classification", "Group",
                       "Consent", "Visit", "Sex", "Age"]
            rows = []
            for pid in ids_int:
                p = one("""SELECT p.*, s.study_code FROM participants p
                           JOIN studies s ON s.id = p.study_id WHERE p.id=?""", (pid,))
                if p:
                    rows.append([p["study_code"], p["participant_code"],
                                 p["classification"] or "Undetermined",
                                 p["group_type"], p["consent_status"],
                                 p["visit_date"] or "", p["sex"] or "",
                                 p["age"] or ""])
            blob = csv_bytes(headers, rows)
            audit("BULK_EXPORT", ",".join(map(str, ids_int)))
            return send_file(io.BytesIO(blob),
                             download_name="participants_selected.csv",
                             as_attachment=True, mimetype="text/csv")

        return redirect(url_for("participants_list"))
