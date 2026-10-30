"""Critical value alerts — rules + evaluation + acknowledgment."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute
from alerts_engine import evaluate_record, run_all

OPERATORS = [
    ("gt", ">"), ("gte", "≥"), ("lt", "<"), ("lte", "≤"),
    ("eq", "="), ("between", "between"),
]


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

    @app.route("/alerts")
    def alerts_page():
        alerts = query("""SELECT a.*, p.participant_code, pa.name AS pname,
                                 pa.code AS pcode, pa.unit, s.study_code
                          FROM alerts a
                          LEFT JOIN participants p ON p.id=a.participant_id
                          LEFT JOIN parameters pa ON pa.id=a.parameter_id
                          LEFT JOIN studies s ON s.id=p.study_id
                          WHERE a.acknowledged=0
                          ORDER BY a.id DESC LIMIT 500""")
        n_open = len(alerts)
        rules = query("""SELECT r.*, p.name AS pname, p.code AS pcode, p.unit
                         FROM critical_rules r
                         JOIN parameters p ON p.id=r.parameter_id
                         ORDER BY r.id DESC""")
        params = query("""SELECT id,code,name,unit FROM parameters
                          WHERE active=1 ORDER BY category, sort_order, name""")
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived=0 ORDER BY title""")
        return render_template("alerts.html", alerts=alerts, n_open=n_open,
                               rules=rules, params=params, operators=OPERATORS,
                               studies=studies)

    @app.post("/alerts/rules/new")
    @role_required("ADMIN", "RESEARCHER")
    def alert_rule_new():
        pid = request.form.get("parameter_id")
        if not pid:
            flash("Select a parameter.", "danger")
            return redirect(url_for("alerts_page"))
        execute("""INSERT INTO critical_rules
                   (parameter_id, operator, value1, value2, severity, message)
                   VALUES(?,?,?,?,?,?)""",
                (pid,
                 request.form.get("operator", "gt"),
                 request.form.get("value1") or None,
                 request.form.get("value2") or None,
                 request.form.get("severity", "warning"),
                 request.form.get("message", "")))
        flash("Alert rule added.", "success")
        return redirect(url_for("alerts_page"))

    @app.post("/alerts/rules/<int:rid>/delete")
    @role_required("ADMIN", "RESEARCHER")
    def alert_rule_delete(rid):
        execute("DELETE FROM critical_rules WHERE id=?", (rid,))
        flash("Rule removed.", "success")
        return redirect(url_for("alerts_page"))

    @app.post("/alerts/rules/<int:rid>/toggle")
    @role_required("ADMIN", "RESEARCHER")
    def alert_rule_toggle(rid):
        execute("UPDATE critical_rules SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                (rid,))
        return redirect(url_for("alerts_page"))

    @app.post("/alerts/scan")
    @role_required("ADMIN", "RESEARCHER")
    def alerts_scan():
        from database import visible_study_ids
        sid = request.form.get("study_id") or None
        visible = visible_study_ids(g.user)
        if sid:
            # User must be allowed to scan this specific study
            if visible is not None and int(sid) not in visible:
                abort(403)
            n = run_all(sid)
        elif visible is None:
            n = run_all(None)
        else:
            n = 0
            for vsid in visible:
                n += run_all(vsid)
        flash(f"Scanned. {n} new alert(s) generated.", "success" if n == 0 else "warning")
        return redirect(url_for("alerts_page"))

    @app.post("/alerts/<int:aid>/ack")
    @role_required("ADMIN", "RESEARCHER")
    def alert_ack(aid):
        execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (aid,))
        return redirect(url_for("alerts_page"))

    @app.post("/alerts/ack-all")
    @role_required("ADMIN", "RESEARCHER")
    def alerts_ack_all():
        execute("UPDATE alerts SET acknowledged=1 WHERE acknowledged=0")
        flash("All alerts acknowledged.", "success")
        return redirect(url_for("alerts_page"))
