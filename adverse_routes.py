"""Adverse events — list, create, edit, resolve, print."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from database import query, one, execute


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

    @app.route("/adverse")
    def adverse_list():
        rows = query("""
            SELECT a.*, p.participant_code, s.study_code
            FROM adverse_events a
            LEFT JOIN participants p ON p.id = a.participant_id
            LEFT JOIN studies s ON s.id = p.study_id
            ORDER BY a.resolved, a.id DESC LIMIT 500""")
        n_open = one("SELECT COUNT(*) n FROM adverse_events WHERE resolved=0")["n"]
        return render_template("adverse_list.html", rows=rows, n_open=n_open)

    @app.route("/adverse/new", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def adverse_new():
        participants = query("""
            SELECT p.id, p.participant_code, s.study_code
            FROM participants p JOIN studies s ON s.id = p.study_id
            WHERE p.archived = 0 ORDER BY s.study_code, p.participant_code""")
        if request.method == "POST":
            eid = execute("""INSERT INTO adverse_events
                (participant_id, event_date, term, severity, outcome, notes,
                 causality, action_taken, serious)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (request.form["participant_id"],
                 request.form.get("event_date") or None,
                 request.form["term"].strip(),
                 request.form.get("severity", "Mild"),
                 request.form.get("outcome", "Ongoing"),
                 request.form.get("notes", ""),
                 request.form.get("causality", "Not assessed"),
                 request.form.get("action_taken", ""),
                 1 if request.form.get("serious") == "1" else 0))
            audit("CREATE", "adverse_event", eid, request.form["term"])
            flash("Adverse event recorded.", "success")
            return redirect(url_for("adverse_list"))
        return render_template("adverse_form.html", row=None, participants=participants)

    @app.route("/adverse/<int:eid>/edit", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def adverse_edit(eid):
        row = one("SELECT * FROM adverse_events WHERE id=?", (eid,))
        if not row: abort(404)
        participants = query("""
            SELECT p.id, p.participant_code, s.study_code
            FROM participants p JOIN studies s ON s.id = p.study_id
            WHERE p.archived = 0 ORDER BY s.study_code, p.participant_code""")
        if request.method == "POST":
            execute("""UPDATE adverse_events SET
                participant_id=?, event_date=?, term=?, severity=?,
                outcome=?, notes=?, causality=?, action_taken=?, serious=?
                WHERE id=?""",
                (request.form["participant_id"],
                 request.form.get("event_date") or None,
                 request.form["term"].strip(),
                 request.form.get("severity", "Mild"),
                 request.form.get("outcome", "Ongoing"),
                 request.form.get("notes", ""),
                 request.form.get("causality", "Not assessed"),
                 request.form.get("action_taken", ""),
                 1 if request.form.get("serious") == "1" else 0, eid))
            audit("UPDATE", "adverse_event", eid)
            flash("Adverse event updated.", "success")
            return redirect(url_for("adverse_list"))
        return render_template("adverse_form.html", row=row, participants=participants)

    @app.post("/adverse/<int:eid>/resolve")
    @role_required("ADMIN", "RESEARCHER")
    def adverse_resolve(eid):
        execute("UPDATE adverse_events SET resolved = 1 WHERE id=?", (eid,))
        audit("RESOLVE", "adverse_event", eid)
        flash("Marked as resolved.", "success")
        return redirect(url_for("adverse_list"))

    @app.post("/adverse/<int:eid>/delete")
    @role_required("ADMIN")
    def adverse_delete(eid):
        execute("DELETE FROM adverse_events WHERE id=?", (eid,))
        audit("DELETE", "adverse_event", eid)
        flash("Deleted.", "success")
        return redirect(url_for("adverse_list"))

    @app.route("/print/adverse-report")
    def print_adverse_report():
        rows = query("""
            SELECT a.*, p.participant_code, s.study_code
            FROM adverse_events a
            LEFT JOIN participants p ON p.id = a.participant_id
            LEFT JOIN studies s ON s.id = p.study_id
            ORDER BY a.id DESC""")
        return render_template("print_adverse.html", rows=rows)
