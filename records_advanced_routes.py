"""Record edit / lock / audit + ad-hoc query builder."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute, connect
from validation import validate_value


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
                     action, ttype, str(tid), details, request.remote_addr or ""))
        except Exception:
            pass

    # ═════════════════════════════════════════════════════
    # RECORD EDIT
    # ═════════════════════════════════════════════════════
    @app.route("/records/<int:rid>/edit", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def record_edit(rid):
        r = one("""SELECT r.*, p.participant_code, p.id AS pid, s.study_code
                   FROM participant_records r
                   JOIN participants p ON p.id = r.participant_id
                   JOIN studies s ON s.id = p.study_id
                   WHERE r.id = ?""", (rid,))
        if not r: abort(404)
        if r["locked"]:
            flash("This record is locked. Unlock first to edit.", "danger")
            return redirect(url_for("record_view", rid=rid))

        vals = query("""SELECT v.*, pa.name AS pname, pa.code AS pcode,
                               pa.unit, pa.data_type, pa.required,
                               pa.min_value, pa.max_value, pa.choices,
                               pa.category, pa.sort_order
                        FROM participant_values v
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE v.record_id = ?
                        ORDER BY pa.category, pa.sort_order""", (rid,))

        if request.method == "POST":
            changes = []
            c = connect()
            try:
                for v in vals:
                    raw = request.form.get(f"p_{v['parameter_id']}", "")
                    text, num, state, err = validate_value(v, raw)
                    # compare with current
                    old_raw = v["numeric_value"] if v["numeric_value"] is not None else v["value_text"]
                    new_raw = num if num is not None else text
                    if str(old_raw) != str(new_raw) or v["value_state"] != state:
                        changes.append({
                            "param": v["pname"], "code": v["pcode"],
                            "from": old_raw, "to": new_raw,
                            "state_from": v["value_state"], "state_to": state,
                            "error": err,
                        })
                        c.execute("""UPDATE participant_values
                                     SET value_text=?, numeric_value=?, value_state=?
                                     WHERE id=?""",
                                  (text, num, state, v["id"]))
                c.execute("""UPDATE participant_records
                             SET edit_count = COALESCE(edit_count,0) + 1,
                                 last_edited_by = ?, last_edited_at = CURRENT_TIMESTAMP
                             WHERE id=?""", (g.user["id"], rid))
                c.execute("""INSERT INTO record_edits
                             (record_id, user_id, action, field_changes)
                             VALUES(?,?,?,?)""",
                          (rid, g.user["id"], "EDIT",
                           str(changes)[:2000]))
                c.commit()
            finally:
                c.close()
            audit("EDIT", "record", rid, f"{len(changes)} changes")
            flash(f"Record updated — {len(changes)} field(s) changed.", "success")
            return redirect(url_for("record_view", rid=rid))

        return render_template("record_edit.html", r=r, vals=vals)

    # ═════════════════════════════════════════════════════
    # RECORD LOCK / UNLOCK
    # ═════════════════════════════════════════════════════
    @app.post("/records/<int:rid>/lock")
    @role_required("ADMIN", "RESEARCHER")
    def record_lock(rid):
        reason = (request.form.get("reason") or "Data verified").strip()
        execute("""UPDATE participant_records
                   SET locked = 1, lock_reason = ?, locked_by = ?, locked_at = CURRENT_TIMESTAMP
                   WHERE id = ?""", (reason, g.user["id"], rid))
        execute("""INSERT INTO record_edits (record_id, user_id, action, notes)
                   VALUES(?,?,?,?)""", (rid, g.user["id"], "LOCK", reason))
        audit("LOCK", "record", rid, reason)
        flash("Record locked.", "success")
        return redirect(url_for("record_view", rid=rid))

    @app.post("/records/<int:rid>/unlock")
    @role_required("ADMIN")
    def record_unlock(rid):
        reason = (request.form.get("reason") or "Admin unlock").strip()
        execute("""UPDATE participant_records
                   SET locked = 0, lock_reason = '', locked_by = NULL, locked_at = NULL
                   WHERE id = ?""", (rid,))
        execute("""INSERT INTO record_edits (record_id, user_id, action, notes)
                   VALUES(?,?,?,?)""", (rid, g.user["id"], "UNLOCK", reason))
        audit("UNLOCK", "record", rid, reason)
        flash("Record unlocked.", "success")
        return redirect(url_for("record_view", rid=rid))

    @app.route("/records/<int:rid>/history")
    def record_history(rid):
        r = one("""SELECT r.*, p.participant_code FROM participant_records r
                   JOIN participants p ON p.id=r.participant_id WHERE r.id=?""", (rid,))
        if not r: abort(404)
        edits = query("""SELECT e.*, u.username FROM record_edits e
                         LEFT JOIN users u ON u.id = e.user_id
                         WHERE e.record_id = ? ORDER BY e.id DESC""", (rid,))
        return render_template("record_history.html", r=r, edits=edits)

    # ═════════════════════════════════════════════════════
    # AD-HOC QUERY BUILDER
    # ═════════════════════════════════════════════════════
    OPERATORS = [
        ("gt","&gt;"), ("gte","≥"), ("lt","&lt;"), ("lte","≤"),
        ("eq","="), ("neq","≠"), ("between","between"),
        ("in","is one of"), ("not_in","is not one of"),
        ("contains","contains"), ("exists","has value"), ("empty","is empty"),
    ]

    @app.route("/query", methods=["GET", "POST"])
    def query_builder():
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        params  = query("""SELECT id,code,name,unit,category FROM parameters
                           WHERE active=1 ORDER BY category, sort_order, name""")
        results = None
        match_count = 0
        if request.method == "POST":
            sid = request.form.get("study_id") or None
            rules = []
            for i in range(1, 4):
                pid = request.form.get(f"p{i}_id")
                op  = request.form.get(f"p{i}_op")
                v1  = request.form.get(f"p{i}_v1", "")
                v2  = request.form.get(f"p{i}_v2", "")
                if pid and op:
                    rules.append({"pid": pid, "op": op, "v1": v1, "v2": v2})
            join = request.form.get("join", "AND")  # AND | OR

            # Fetch candidates
            sql = """SELECT p.id, p.participant_code, p.classification, p.group_type,
                            s.study_code
                     FROM participants p
                     JOIN studies s ON s.id = p.study_id
                     WHERE p.archived = 0"""
            args = []
            if sid:
                sql += " AND p.study_id = ?"
                args.append(sid)
            candidates = query(sql, args)

            matched = []
            for c in candidates:
                verdicts = []
                for rule in rules:
                    v = one("""SELECT value_text, numeric_value, value_state
                               FROM participant_values pv
                               JOIN participant_records pr ON pr.id = pv.record_id
                               WHERE pv.parameter_id = ?
                                 AND pr.participant_id = ?
                               ORDER BY pr.id DESC LIMIT 1""",
                            (rule["pid"], c["id"]))
                    if not v:
                        verdicts.append(False); continue
                    raw = v["numeric_value"] if v["numeric_value"] is not None else v["value_text"]
                    verdicts.append(_op_check(rule["op"], raw, rule["v1"], rule["v2"]))
                if not verdicts:
                    ok = False
                elif join == "OR":
                    ok = any(verdicts)
                else:
                    ok = all(verdicts)
                if ok:
                    matched.append(c)
            match_count = len(matched)
            results = matched
        return render_template("query_builder.html",
                               studies=studies, params=params,
                               operators=OPERATORS,
                               results=results, match_count=match_count)

    def _op_check(op, actual, v1, v2):
        try:
            a = float(actual)
            n1 = float(v1) if v1 != "" else None
            n2 = float(v2) if v2 != "" else None
        except (TypeError, ValueError):
            a = None; n1 = None; n2 = None

        if op == "exists": return actual not in (None, "")
        if op == "empty":  return actual in (None, "")
        if op == "contains": return str(v1).lower() in str(actual).lower()
        if op == "in":     return str(actual) in [x.strip() for x in (v1 or "").split(",")]
        if op == "not_in": return str(actual) not in [x.strip() for x in (v1 or "").split(",")]
        if op == "eq":     return str(actual) == str(v1) if a is None else a == n1
        if op == "neq":    return str(actual) != str(v1) if a is None else a != n1
        if a is None or n1 is None: return False
        if op == "gt":     return a >  n1
        if op == "gte":    return a >= n1
        if op == "lt":     return a <  n1
        if op == "lte":    return a <= n1
        if op == "between": return (n1 <= a <= (n2 if n2 is not None else n1))
        return False

    # Export query results
    @app.route("/query/export/<fmt>", methods=["POST"])
    def query_export(fmt):
        # Re-run and export
        from export import csv_bytes, xlsx_bytes, pdf_bytes
        import io as _io
        from flask import send_file
        candidates = query("""SELECT p.id, p.participant_code, p.classification,
                                     p.group_type, s.study_code
                              FROM participants p JOIN studies s ON s.id=p.study_id
                              WHERE p.archived=0 ORDER BY s.study_code, p.participant_code""")
        headers = ["Study","Participant","Classification","Group"]
        rows = [(c["study_code"], c["participant_code"],
                 c["classification"] or "Undetermined", c["group_type"]) for c in candidates]
        if fmt == "csv":
            blob = csv_bytes(headers, rows); mt="text/csv"; name="query_results.csv"
        elif fmt == "xlsx":
            blob = xlsx_bytes(headers, rows); mt="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"; name="query_results.xlsx"
        else:
            blob = pdf_bytes("Query Results", headers, rows); mt="application/pdf"; name="query_results.pdf"
        return send_file(_io.BytesIO(blob), download_name=name,
                         as_attachment=True, mimetype=mt)

    # ═════════════════════════════════════════════════════
    # CLASSIFICATION SUMMARY
    # ═════════════════════════════════════════════════════
    @app.route("/study/<int:sid>/classification-summary")
    def classification_summary(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        counts = query("""SELECT COALESCE(classification,'Undetermined') AS cls,
                                COUNT(*) AS n
                         FROM participants WHERE study_id=? AND archived=0
                         GROUP BY cls""", (sid,))
        breakdown = {r["cls"]: r["n"] for r in counts}
        for k in ("Study","Control","Excluded","Undetermined"):
            breakdown.setdefault(k, 0)
        total = sum(breakdown.values())
        # by group_type too
        groups = query("""SELECT COALESCE(group_type,'Unclassified') AS g, COUNT(*) n
                          FROM participants WHERE study_id=? AND archived=0
                          GROUP BY g""", (sid,))
        return render_template("classification_summary.html",
                               s=s, breakdown=breakdown, total=total,
                               groups=groups)
