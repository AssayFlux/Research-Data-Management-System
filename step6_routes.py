"""Step 6 — Export (CSV/XLSX/PDF) + Import CSV + Print buttons."""
import io, csv
from functools import wraps
from datetime import datetime
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, send_file, jsonify, session)
from database import query, one, execute, visible_study_ids, can_access_study

def _rows_for_study(sid=None, pid=None):
    sql = """SELECT s.study_code, p.participant_code, p.group_type,
                    r.visit_date, pa.category, pa.name AS pname, pa.code AS pcode,
                    pa.unit, v.numeric_value, v.value_text, v.value_state,
                    pa.ref_low, pa.ref_high, pa.ref_text
             FROM participant_values v
             JOIN participant_records r ON r.id = v.record_id
             JOIN participants p ON p.id = r.participant_id
             JOIN studies s ON s.id = p.study_id
             JOIN parameters pa ON pa.id = v.parameter_id
             WHERE 1=1"""
    args = []
    if sid:
        sql += " AND s.id = ?"; args.append(sid)
    if pid:
        sql += " AND p.id = ?"; args.append(pid)
    sql += " ORDER BY s.study_code, p.participant_code, pa.sort_order"
    return query(sql, args)


def _rows_for_visible_studies(study_ids):
    if not study_ids:
        return []
    ph = ",".join("?" for _ in study_ids)
    sql = """SELECT s.study_code, p.participant_code, p.group_type,
                    r.visit_date, pa.category, pa.name AS pname, pa.code AS pcode,
                    pa.unit, v.numeric_value, v.value_text, v.value_state,
                    pa.ref_low, pa.ref_high, pa.ref_text
             FROM participant_values v
             JOIN participant_records r ON r.id = v.record_id
             JOIN participants p ON p.id = r.participant_id
             JOIN studies s ON s.id = p.study_id
             JOIN parameters pa ON pa.id = v.parameter_id
             WHERE s.id IN (""" + ph + ") ORDER BY s.study_code, p.participant_code, pa.sort_order"
    return query(sql, list(study_ids))


def _table(headers, data_rows):
    return [list(headers)] + [list(map(lambda x: "" if x is None else x, r)) for r in data_rows]


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

    def audit(action, ttype="", tid="", details=""):
        try:
            execute("""INSERT INTO audit_log
                       (user_id,action,target_type,target_id,details,ip)
                       VALUES(?,?,?,?,?,?)""",
                    (g.user["id"] if getattr(g, "user", None) else None,
                     action, ttype, str(tid), details,
                     request.remote_addr or ""))
        except Exception:
            pass

    # ============================================================
    # EXPORT PAGE
    # ============================================================
    @app.route("/export")
    def export_page():
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        return render_template("export.html", studies=studies)

    # ============================================================
    # DATASET EXPORTS
    # ============================================================
    def _export(fmt, sid=None, pid=None, label="research_data"):
        from export import csv_bytes, xlsx_bytes, pdf_bytes
        # Never let a non-admin export outside their assigned studies.
        if g.user["role"] != "ADMIN":
            visible = visible_study_ids(g.user)
            if sid is not None and not can_access_study(g.user, sid):
                abort(403)
            if pid is not None:
                owner = one("SELECT study_id FROM participants WHERE id=?", (pid,))
                if not owner or not can_access_study(g.user, owner["study_id"]):
                    abort(403)
            if sid is None and pid is None:
                if not visible:
                    rows = []
                else:
                    ph = ",".join("?" for _ in visible)
                    rows = _rows_for_visible_studies(visible)
            else:
                rows = _rows_for_study(sid, pid)
        else:
            rows = _rows_for_study(sid, pid)
        headers = ["Study", "Participant", "Group", "Visit date",
                   "Category", "Parameter", "Code", "Unit",
                   "Numeric value", "Text value", "State",
                   "Ref low", "Ref high", "Ref text"]
        data = [(
            r["study_code"], r["participant_code"], r["group_type"],
            r["visit_date"] or "", r["category"] or "", r["pname"], r["pcode"],
            r["unit"] or "", r["numeric_value"] if r["numeric_value"] is not None else "",
            r["value_text"] or "", r["value_state"],
            r["ref_low"] if r["ref_low"] is not None else "",
            r["ref_high"] if r["ref_high"] is not None else "",
            r["ref_text"] or "",
        ) for r in rows]

        title = "Research Data Export"
        sub = f"{len(data)} rows · generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        if fmt == "csv":
            blob = csv_bytes(headers, data)
            mt = "text/csv"; name = f"{label}.csv"
        elif fmt == "xlsx":
            blob = xlsx_bytes(headers, data, sheet="Research Data")
            mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            name = f"{label}.xlsx"
        elif fmt == "pdf":
            blob = pdf_bytes(title, headers, data, sub)
            mt = "application/pdf"; name = f"{label}.pdf"
        else:
            abort(404)
        audit("EXPORT", "dataset", label, fmt)
        return send_file(io.BytesIO(blob), download_name=name,
                         as_attachment=True, mimetype=mt)

    @app.route("/export/all/<fmt>")
    def export_all(fmt):
        return _export(fmt, label="research_data_all")

    @app.route("/export/study/<int:sid>/<fmt>")
    def export_study(sid, fmt):
        s = one("SELECT study_code FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        return _export(fmt, sid=sid, label=f"study_{s['study_code']}")

    @app.route("/export/participant/<int:pid>/<fmt>")
    def export_participant(pid, fmt):
        p = one("SELECT participant_code FROM participants WHERE id=?", (pid,))
        if not p: abort(404)
        return _export(fmt, pid=pid, label=f"participant_{p['participant_code']}")

    # ============================================================
    # IMPORT (CSV upload + column mapping + commit)
    # ============================================================
    @app.route("/import")
    @role_required("ADMIN", "RESEARCHER")
    def import_page():
        return render_template("import.html", preview=None, headers=None, rows=None)

    @app.route("/import/preview", methods=["POST"])
    @role_required("ADMIN", "RESEARCHER")
    def import_preview():
        f = request.files.get("csv_file")
        if not f or not f.filename:
            flash("Choose a CSV file.", "danger")
            return redirect(url_for("import_page"))
        try:
            raw = f.read().decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(raw))
            all_rows = list(reader)
            if not all_rows:
                flash("CSV is empty.", "danger")
                return redirect(url_for("import_page"))
            headers = all_rows[0]
            rows = all_rows[1:51]
            total = len(all_rows) - 1
            flash(f"File: {f.filename} · {total} data rows detected.", "success")
            return render_template("import.html",
                                   headers=headers, rows=rows,
                                   preview=True, total=total,
                                   csv_text=raw[:200000])
        except Exception as e:
            flash(f"Could not read file: {e}", "danger")
            return redirect(url_for("import_page"))

    @app.route("/import/commit", methods=["POST"])
    @role_required("ADMIN", "RESEARCHER")
    def import_commit():
        study_id = request.form.get("study_id")
        if not study_id:
            flash("Choose a target study.", "danger")
            return redirect(url_for("import_page"))
        f = request.files.get("csv_file")
        if not f or not f.filename:
            flash("CSV missing — start over.", "danger")
            return redirect(url_for("import_page"))
        raw = f.read().decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(raw))
        all_rows = list(reader)
        if len(all_rows) < 2:
            flash("CSV has no data rows.", "danger")
            return redirect(url_for("import_page"))

        headers = all_rows[0]
        data_rows = all_rows[1:]

        # Expected layout: code, param_code, value  (or code, category, param, value)
        # We detect simple long format: [participant_code, parameter_code, value]
        # Users can adapt the columns as they wish later; this is the safe default.
        try:
            n_part = n_values = 0
            seen_parts = {}
            for row in data_rows:
                if len(row) < 3: continue
                pcode = (row[0] or "").strip()
                pa_code = (row[1] or "").strip()
                val = (row[2] or "").strip()
                if not pcode or not pa_code: continue

                # Participant — create if missing
                if pcode not in seen_parts:
                    p = one("""SELECT id FROM participants
                               WHERE study_id=? AND participant_code=?""",
                            (study_id, pcode))
                    if p:
                        seen_parts[pcode] = p["id"]
                    else:
                        pid_new = execute("""INSERT INTO participants
                            (study_id, participant_code) VALUES(?,?)""",
                            (study_id, pcode))
                        seen_parts[pcode] = pid_new
                        n_part += 1
                pid = seen_parts[pcode]

                # Parameter lookup by code
                param = one("""SELECT id, data_type FROM parameters
                               WHERE code=? AND active=1""", (pa_code,))
                if not param: continue

                # One record per participant for the whole file
                rec = one("""SELECT id FROM participant_records
                             WHERE participant_id=? ORDER BY id LIMIT 1""", (pid,))
                if rec:
                    rid = rec["id"]
                else:
                    rid = execute("""INSERT INTO participant_records
                                     (participant_id, created_by) VALUES(?,?)""",
                                  (pid, g.user["id"]))

                num = None
                try: num = float(val) if val != "" else None
                except ValueError: pass
                state = "VALUE" if val != "" else "MISSING"
                execute("""INSERT INTO participant_values
                           (record_id, parameter_id, value_text,
                            numeric_value, value_state)
                           VALUES(?,?,?,?,?)
                           ON CONFLICT(record_id,parameter_id) DO UPDATE SET
                           value_text=excluded.value_text,
                           numeric_value=excluded.numeric_value,
                           value_state=excluded.value_state""",
                        (rid, param["id"], None if num is not None else val,
                         num, state))
                n_values += 1
            audit("IMPORT", "csv", study_id,
                  f"participants={n_part} values={n_values}")
            flash(f"Imported {n_values} values across "
                  f"{len(seen_parts)} participant(s).", "success")
        except Exception as e:
            flash(f"Import failed: {e}", "danger")
        return redirect(url_for("import_page"))

    # ============================================================
    # CSV TEMPLATE DOWNLOAD
    # ============================================================
    @app.route("/import/template")
    @role_required("ADMIN", "RESEARCHER")
    def import_template():
        headers = ["participant_code", "parameter_code", "value"]
        sample = [
            ["P001", "age", "34"],
            ["P001", "weight", "72.5"],
            ["P001", "fbs", "92"],
            ["P002", "age", "29"],
        ]
        blob = csv_bytes(headers, sample)
        audit("DOWNLOAD", "template", "import_csv")
        return send_file(io.BytesIO(blob),
                         download_name="import_template.csv",
                         as_attachment=True, mimetype="text/csv")
