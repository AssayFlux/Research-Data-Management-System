"""Visit scheduling + biospecimen tracking."""
from datetime import date, datetime
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
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

    # ── Visits: page for one participant ──
    @app.route("/participants/<int:pid>/visits")
    def participant_visits(pid):
        p = one("""SELECT p.*, s.study_code FROM participants p
                   JOIN studies s ON s.id=p.study_id WHERE p.id=?""", (pid,))
        if not p: abort(404)
        rows = query("""SELECT * FROM visit_schedules WHERE participant_id=?
                        ORDER BY visit_number, target_date""", (pid,))
        # overdue calculation
        today = date.today().isoformat()
        for r in rows:
            r_dict = dict(r)
            r_dict["overdue"] = (r["status"] == "Scheduled"
                                 and r["target_date"] and r["target_date"] < today)
            yield_from_rows = None
            # can't mutate row easily, wrap
            rows_processed = None
        # Build a simple list of dicts
        visits = []
        for r in rows:
            d = dict(r)
            d["overdue"] = (r["status"] == "Scheduled" and
                            r["target_date"] and r["target_date"] < today)
            visits.append(d)
        return render_template("participant_visits.html", p=p, visits=visits)

    @app.post("/participants/<int:pid>/visits/new")
    @role_required("ADMIN", "RESEARCHER")
    def visit_new(pid):
        if not one("SELECT id FROM participants WHERE id=?", (pid,)): abort(404)
        execute("""INSERT INTO visit_schedules
                   (participant_id, visit_number, visit_name, target_date,
                    actual_date, status, notes)
                   VALUES(?,?,?,?,?,?,?)""",
                (pid,
                 int(request.form.get("visit_number") or 1),
                 request.form.get("visit_name", "Visit"),
                 request.form.get("target_date") or None,
                 request.form.get("actual_date") or None,
                 request.form.get("status", "Scheduled"),
                 request.form.get("notes", "")))
        flash("Visit scheduled.", "success")
        return redirect(url_for("participant_visits", pid=pid))

    @app.post("/visits/<int:vid>/update")
    @role_required("ADMIN", "RESEARCHER")
    def visit_update(vid):
        v = one("SELECT * FROM visit_schedules WHERE id=?", (vid,))
        if not v: abort(404)
        execute("""UPDATE visit_schedules SET visit_name=?, target_date=?,
                   actual_date=?, status=?, notes=? WHERE id=?""",
                (request.form.get("visit_name", v["visit_name"]),
                 request.form.get("target_date") or None,
                 request.form.get("actual_date") or None,
                 request.form.get("status", v["status"]),
                 request.form.get("notes", ""), vid))
        flash("Visit updated.", "success")
        return redirect(url_for("participant_visits", pid=v["participant_id"]))

    @app.post("/visits/<int:vid>/delete")
    @role_required("ADMIN", "RESEARCHER")
    def visit_delete(vid):
        v = one("SELECT * FROM visit_schedules WHERE id=?", (vid,))
        if not v: abort(404)
        execute("DELETE FROM visit_schedules WHERE id=?", (vid,))
        flash("Visit removed.", "success")
        return redirect(url_for("participant_visits", pid=v["participant_id"]))

    # ── Upcoming visits dashboard ──
    @app.route("/visits/upcoming")
    def visits_upcoming():
        today = date.today().isoformat()
        studies = query("SELECT id,study_code FROM studies WHERE archived=0 ORDER BY title")
        sid = request.args.get("study_id", type=int)
        sql = """SELECT v.*, p.participant_code, p.id AS pid, s.study_code
                 FROM visit_schedules v
                 JOIN participants p ON p.id = v.participant_id
                 JOIN studies s ON s.id = p.study_id
                 WHERE p.archived=0"""
        args = []
        if sid:
            sql += " AND p.study_id=?"; args.append(sid)
        sql += " ORDER BY v.target_date IS NULL, v.target_date"
        rows = query(sql, args)
        visits = []
        for r in rows:
            d = dict(r)
            d["overdue"] = (r["status"] == "Scheduled" and
                            r["target_date"] and r["target_date"] < today)
            visits.append(d)
        upcoming = [v for v in visits if v["status"] == "Scheduled"][:60]
        overdue  = [v for v in visits if v["overdue"]][:40]
        completed = [v for v in visits if v["status"] == "Completed"][:20]
        return render_template("visits_upcoming.html",
                               upcoming=upcoming, overdue=overdue,
                               completed=completed, studies=studies, selected=sid)

    # ── Biospecimens ──
    @app.route("/participants/<int:pid>/specimens")
    def participant_specimens(pid):
        p = one("""SELECT p.*, s.study_code FROM participants p
                   JOIN studies s ON s.id=p.study_id WHERE p.id=?""", (pid,))
        if not p: abort(404)
        rows = query("""SELECT * FROM biospecimens WHERE participant_id=?
                        ORDER BY collection_date DESC, id DESC""", (pid,))
        return render_template("participant_specimens.html", p=p, rows=rows)

    @app.post("/participants/<int:pid>/specimens/new")
    @role_required("ADMIN", "RESEARCHER")
    def specimen_new(pid):
        if not one("SELECT id FROM participants WHERE id=?", (pid,)): abort(404)
        execute("""INSERT INTO biospecimens
                   (participant_id, sample_id, sample_type, collection_date,
                    storage_location, freeze_thaw, volume, notes)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (pid,
                 request.form.get("sample_id", "").strip(),
                 request.form.get("sample_type", ""),
                 request.form.get("collection_date") or None,
                 request.form.get("storage_location", ""),
                 int(request.form.get("freeze_thaw") or 0),
                 request.form.get("volume", ""),
                 request.form.get("notes", "")))
        flash("Biospecimen recorded.", "success")
        return redirect(url_for("participant_specimens", pid=pid))

    @app.post("/specimens/<int:sid>/delete")
    @role_required("ADMIN", "RESEARCHER")
    def specimen_delete(sid):
        s = one("SELECT * FROM biospecimens WHERE id=?", (sid,))
        if not s: abort(404)
        execute("DELETE FROM biospecimens WHERE id=?", (sid,))
        flash("Specimen removed.", "success")
        return redirect(url_for("participant_specimens", pid=s["participant_id"]))

    @app.route("/specimens")
    def specimens_all():
        studies = query("SELECT id,study_code FROM studies WHERE archived=0 ORDER BY title")
        sid = request.args.get("study_id", type=int)
        sql = """SELECT b.*, p.participant_code, p.id AS pid, s.study_code
                 FROM biospecimens b
                 JOIN participants p ON p.id=b.participant_id
                 JOIN studies s ON s.id=p.study_id
                 WHERE p.archived=0"""
        args = []
        if sid:
            sql += " AND p.study_id=?"; args.append(sid)
        sql += " ORDER BY b.id DESC LIMIT 500"
        rows = query(sql, args)
        return render_template("specimens_all.html", rows=rows,
                               studies=studies, selected=sid)
