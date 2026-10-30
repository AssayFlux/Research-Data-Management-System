"""De-identified export — HMAC-hashed subject codes, age banding, visit shifting."""
import io, hmac, hashlib, secrets
from datetime import datetime, date, timedelta
from flask import (render_template, request, send_file, abort,
                   g, flash)
from database import query, one, execute
from export import csv_bytes, xlsx_bytes, pdf_bytes


def _hash(subject, salt, prefix="S"):
    h = hmac.new(salt.encode(), subject.encode(), hashlib.sha256).hexdigest()[:10].upper()
    return f"{prefix}{h}"


def _age_band(age):
    if age is None: return "—"
    if age < 18: return "<18"
    if age < 30: return "18–29"
    if age < 45: return "30–44"
    if age < 60: return "45–59"
    return "≥60"


def register(app):

    @app.route("/export/deidentify", methods=["GET", "POST"])
    def deidentify_export():
        if not g.user or g.user["role"] not in ("ADMIN", "RESEARCHER"):
            abort(403)
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")

        if request.method == "POST":
            study_id       = request.form.get("study_id") or None
            fmt            = request.form.get("fmt", "csv")
            strip_demo     = bool(request.form.get("strip_demographic"))
            shift_dates    = bool(request.form.get("shift_dates"))
            salt           = request.form.get("salt") or secrets.token_hex(8)

            where = "WHERE 1=1"; args = []
            if study_id:
                where += " AND p.study_id = ?"; args.append(study_id)

            rows = query(f"""SELECT s.study_code, p.participant_code, p.id AS pid,
                                    p.classification, p.group_type,
                                    p.age, p.sex,
                                    r.id AS record_id, r.visit_date,
                                    pa.code AS pcode, pa.name AS pname, pa.unit,
                                    v.numeric_value, v.value_text, v.value_state
                             FROM participant_values v
                             JOIN participant_records r ON r.id=v.record_id
                             JOIN participants p ON p.id=r.participant_id
                             JOIN studies s ON s.id=p.study_id
                             JOIN parameters pa ON pa.id=v.parameter_id
                             {where}
                             ORDER BY p.id, pa.sort_order""", args)

            # Per-participant date shift (stable offset per subject)
            def shifted(d, pid):
                if not d: return ""
                if not shift_dates: return d
                off = int(hashlib.sha256(f"{salt}:{pid}".encode()).hexdigest()[:4], 16) % 60 - 30
                try:
                    dt = datetime.strptime(d, "%Y-%m-%d").date()
                    return (dt + timedelta(days=off)).isoformat()
                except Exception:
                    return d

            headers = ["Study","Subject","Classification","Group","AgeBand","Sex",
                       "VisitDate","Parameter code","Parameter","Unit","Value","State"]
            data = []
            for r in rows:
                data.append([
                    r["study_code"],
                    _hash(r["participant_code"], salt),
                    r["classification"] or "Undetermined",
                    r["group_type"] or "",
                    "—" if strip_demo else _age_band(r["age"]),
                    "—" if strip_demo else (r["sex"] or ""),
                    shifted(r["visit_date"], r["pid"]),
                    r["pcode"], r["pname"], r["unit"] or "",
                    r["numeric_value"] if r["numeric_value"] is not None
                    else (r["value_text"] or ""),
                    r["value_state"],
                ])
            title = "De-identified Research Data"
            sub = (f"{len(data)} rows · {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                   f"Salt: {salt}")

            if fmt == "csv":
                blob = csv_bytes(headers, data); mt = "text/csv"; name = "deidentified.csv"
            elif fmt == "xlsx":
                blob = xlsx_bytes(headers, data, "De-identified")
                mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                name = "deidentified.xlsx"
            else:
                blob = pdf_bytes(title, headers, data, sub)
                mt = "application/pdf"; name = "deidentified.pdf"

            try:
                execute("""INSERT INTO audit_log (user_id, action, target_type, details)
                           VALUES(?, 'DEIDENTIFY_EXPORT', 'dataset', ?)""",
                        (g.user["id"],
                         f"study={study_id} fmt={fmt} salt={salt[:6]}..."))
            except Exception: pass

            flash(f"Exported. Keep this salt for traceability: {salt}", "info")
            return send_file(io.BytesIO(blob), download_name=name,
                             as_attachment=True, mimetype=mt)

        return render_template("deidentify.html", studies=studies)
