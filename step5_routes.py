"""Step 5 — Statistics, Graphs, Data Quality, Print."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute
from statistics import (descriptive, normality_test, compare_groups,
                        correlation, anova_oneway)

def _param_values(parameter_id, study_id=None):
    """Return rows with numeric_value, group_type, participant_code."""
    sql = """SELECT v.numeric_value, v.value_state,
                    p.group_type, p.participant_code, p.id AS pid
             FROM participant_values v
             JOIN participant_records r ON r.id = v.record_id
             JOIN participants p ON p.id = r.participant_id
             WHERE v.parameter_id = ?"""
    args = [parameter_id]
    if study_id:
        sql += " AND p.study_id = ?"
        args.append(study_id)
    return query(sql, args)

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

    # ================================================================
    # STATISTICS
    # ================================================================
    @app.route("/statistics")
    def statistics_page():
        params = query("""SELECT id,code,name,unit,category FROM parameters
                          WHERE active = 1 ORDER BY category, sort_order, name""")
        studies = query("""SELECT id,study_code,title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        return render_template("statistics.html", params=params, studies=studies)

    @app.post("/statistics/describe")
    def statistics_describe():
        pid = request.form.get("parameter_id")
        sid = request.form.get("study_id") or None
        if not pid:
            return jsonify(error="Select a parameter"), 400
        rows = _param_values(pid, sid)
        values = [r["numeric_value"] for r in rows
                  if r["value_state"] == "VALUE" and r["numeric_value"] is not None]
        missing = sum(1 for r in rows if r["value_state"] != "VALUE")
        out = descriptive(values)
        out["missing"] = missing
        out["total_rows"] = len(rows)
        return jsonify(out)

    @app.post("/statistics/compare")
    def statistics_compare():
        pid = request.form.get("parameter_id")
        sid = request.form.get("study_id") or None
        if not pid:
            return jsonify(error="Select a parameter"), 400
        rows = _param_values(pid, sid)
        groups = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None:
                continue
            g = r["group_type"] or "Unclassified"
            groups.setdefault(g, []).append(r["numeric_value"])
        if len(groups) < 2:
            return jsonify(error="Need at least two groups. Create participants with different group types.")
        names = sorted(groups.keys())
        a_name, b_name = names[0], names[1]
        a, b = groups[a_name], groups[b_name]
        result = compare_groups(a, b)
        result["group_a"] = a_name
        result["group_b"] = b_name
        result["n_a"] = len(a)
        result["n_b"] = len(b)
        result["mean_a"] = round(sum(a) / len(a), 4) if a else 0
        result["mean_b"] = round(sum(b) / len(b), 4) if b else 0
        return jsonify(result)

    @app.post("/statistics/correlate")
    def statistics_correlate():
        xid = request.form.get("x_id")
        yid = request.form.get("y_id")
        method = request.form.get("method", "pearson")
        sid = request.form.get("study_id") or None
        if not xid or not yid:
            return jsonify(error="Pick two parameters"), 400
        sql = """SELECT r.id AS record_id, v.parameter_id, v.numeric_value, v.value_state
                 FROM participant_values v
                 JOIN participant_records r ON r.id = v.record_id
                 JOIN participants p ON p.id = r.participant_id
                 WHERE v.parameter_id IN (?, ?)"""
        args = [xid, yid]
        if sid:
            sql += " AND p.study_id = ?"
            args.append(sid)
        rows = query(sql, args)
        by_rec = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None:
                continue
            by_rec.setdefault(r["record_id"], {})[r["parameter_id"]] = r["numeric_value"]
        xs, ys = [], []
        for rec_id, d in by_rec.items():
            if int(xid) in d and int(yid) in d:
                xs.append(d[int(xid)]); ys.append(d[int(yid)])
        result = correlation(xs, ys, method)
        return jsonify(result)

    # ================================================================
    # GRAPHS
    # ================================================================
    @app.route("/graphs")
    def graphs_page():
        params = query("""SELECT id,code,name,unit,category FROM parameters
                          WHERE active = 1 ORDER BY category, sort_order, name""")
        studies = query("""SELECT id,study_code,title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        return render_template("graphs.html", params=params, studies=studies)

    
    @app.route("/quality")
    def quality_page():
        rows = query("""SELECT q.*, p.participant_code,
                               pa.name AS parameter_name, pa.code AS parameter_code
                        FROM quality_checks q
                        LEFT JOIN participants p ON p.id = q.participant_id
                        LEFT JOIN parameters pa ON pa.id = q.parameter_id
                        ORDER BY q.resolved, q.id DESC LIMIT 500""")
        n_open = one("SELECT COUNT(*) n FROM quality_checks WHERE resolved=0")["n"]
        return render_template("quality.html", rows=rows, n_open=n_open)

    @app.post("/quality/run")
    @role_required("ADMIN", "RESEARCHER")
    def quality_run():
        execute("DELETE FROM quality_checks WHERE resolved = 0")
        issues = 0

        # 1. Values out of min/max or reference range
        rows = query("""SELECT v.numeric_value, v.parameter_id,
                               p.id AS pid, p.participant_code,
                               pa.name AS pname, pa.min_value, pa.max_value,
                               pa.ref_low, pa.ref_high
                        FROM participant_values v
                        JOIN participant_records r ON r.id = v.record_id
                        JOIN participants p ON p.id = r.participant_id
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE v.value_state = 'VALUE' AND v.numeric_value IS NOT NULL""")
        for r in rows:
            msgs = []
            n = r["numeric_value"]
            if r["min_value"] is not None and n < r["min_value"]:
                msgs.append(f"below min ({r['min_value']})")
            if r["max_value"] is not None and n > r["max_value"]:
                msgs.append(f"above max ({r['max_value']})")
            if r["ref_low"] is not None and n < r["ref_low"]:
                msgs.append(f"below reference low ({r['ref_low']})")
            if r["ref_high"] is not None and n > r["ref_high"]:
                msgs.append(f"above reference high ({r['ref_high']})")
            for m in msgs:
                execute("""INSERT INTO quality_checks
                           (participant_id, parameter_id, severity, message)
                           VALUES(?,?,?,?)""",
                        (r["pid"], r["parameter_id"], "warning",
                         f"{r['pname']} = {n}: {m}"))
                issues += 1

        # 2. Required parameters that are missing
        required = query("SELECT id, name FROM parameters WHERE active=1 AND required=1")
        for pa in required:
            recs = query("""SELECT r.id, r.participant_id, p.participant_code
                            FROM participant_records r
                            JOIN participants p ON p.id = r.participant_id""")
            for rec in recs:
                v = one("""SELECT value_state FROM participant_values
                           WHERE record_id = ? AND parameter_id = ?""",
                        (rec["id"], pa["id"]))
                if not v or v["value_state"] != "VALUE":
                    execute("""INSERT INTO quality_checks
                               (participant_id, parameter_id, severity, message)
                               VALUES(?,?,?,?)""",
                            (rec["participant_id"], pa["id"], "warning",
                             f"{pa['name']}: required value missing"))
                    issues += 1

        # 3. Duplicate participant codes across studies
        dups = query("""SELECT participant_code, COUNT(*) n
                        FROM participants WHERE archived = 0
                        GROUP BY participant_code HAVING n > 1""")
        for d in dups:
            execute("""INSERT INTO quality_checks
                       (participant_id, parameter_id, severity, message)
                       VALUES(?,?,?,?)""",
                    (None, None, "info",
                     f"Code '{d['participant_code']}' appears in {d['n']} studies"))
            issues += 1

        execute("""INSERT INTO audit_log (user_id, action, target_type, details)
                   VALUES (?, 'QUALITY_SCAN', 'quality_checks', ?)""",
                (g.user["id"], f"{issues} issues"))
        return jsonify(ok=True, issues=issues)

    @app.post("/quality/<int:qid>/resolve")
    @role_required("ADMIN", "RESEARCHER")
    def quality_resolve(qid):
        execute("UPDATE quality_checks SET resolved = 1 WHERE id = ?", (qid,))
        return jsonify(ok=True)

    # ================================================================
    # PRINT
    # ================================================================
    @app.route("/print/participant/<int:pid>")
    def print_participant(pid):
        p = one("""SELECT p.*, s.study_code, s.title AS study_title,
                          s.pi, s.institution, s.department
                   FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)
        records = query("""SELECT r.*, u.username FROM participant_records r
                           LEFT JOIN users u ON u.id = r.created_by
                           WHERE r.participant_id = ? ORDER BY r.id""", (pid,))
        data = []
        for r in records:
            vals = query("""SELECT v.*, pa.name AS pname, pa.code AS pcode,
                                   pa.unit, pa.category, pa.ref_low, pa.ref_high, pa.ref_text
                            FROM participant_values v
                            JOIN parameters pa ON pa.id = v.parameter_id
                            WHERE v.record_id = ? ORDER BY pa.sort_order""", (r["id"],))
            data.append({"record": r, "values": vals})
        return render_template("print_participant.html", p=p, records_data=data)

    @app.route("/print/study/<int:sid>")
    def print_study(sid):
        s = one("SELECT * FROM studies WHERE id = ?", (sid,))
        if not s: abort(404)
        parts = query("""SELECT * FROM participants
                         WHERE study_id = ? AND archived = 0
                         ORDER BY participant_code""", (sid,))
        return render_template("print_study.html", s=s, parts=parts)

    @app.route("/print/records")
    def print_records():
        rows = query("""SELECT r.id, r.visit_date, r.created_at,
                               p.participant_code, s.study_code, u.username
                        FROM participant_records r
                        JOIN participants p ON p.id = r.participant_id
                        JOIN studies s ON s.id = p.study_id
                        LEFT JOIN users u ON u.id = r.created_by
                        ORDER BY r.id DESC LIMIT 500""")
        return render_template("print_records.html", rows=rows)
