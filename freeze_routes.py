"""Study freeze — lock all edits after a cut-off date."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute


def register(app):
    def role_required(*roles):
        def deco(fn):
            @wraps(fn)
            def wrapper(*a, **kw):
                if not g.user or g.user["role"] not in roles: abort(403)
                return fn(*a, **kw)
            return wrapper
        return deco

    @app.route("/study/<int:sid>/freeze", methods=["GET", "POST"])
    @role_required("ADMIN")
    def study_freeze(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        if request.method == "POST":
            action = request.form.get("action")
            reason = (request.form.get("reason") or "").strip()
            cutoff = request.form.get("cutoff_date") or None
            if action == "freeze":
                execute("""UPDATE studies SET frozen=1, frozen_at=CURRENT_TIMESTAMP,
                           frozen_by=?, freeze_reason=?, cutoff_date=? WHERE id=?""",
                        (g.user["id"], reason, cutoff, sid))
                execute("""INSERT INTO freeze_log(study_id, action, reason, user_id)
                           VALUES(?,?,?,?)""", (sid, "FREEZE", reason, g.user["id"]))
                flash("Study frozen. Data locked.", "success")
            elif action == "unfreeze":
                if not reason:
                    flash("A reason is required to unfreeze.", "danger")
                    return redirect(url_for("study_freeze", sid=sid))
                execute("""UPDATE studies SET frozen=0, freeze_reason=?, cutoff_date=NULL
                           WHERE id=?""", (reason, sid))
                execute("""INSERT INTO freeze_log(study_id, action, reason, user_id)
                           VALUES(?,?,?,?)""", (sid, "UNFREEZE", reason, g.user["id"]))
                flash("Study unfrozen.", "warning")
            return redirect(url_for("study_freeze", sid=sid))
        log = query("""SELECT f.*, u.username FROM freeze_log f
                       LEFT JOIN users u ON u.id=f.user_id
                       WHERE f.study_id=? ORDER BY f.id DESC""", (sid,))
        return render_template("freeze.html", s=s, log=log)

    @app.route("/study/<int:sid>/is-frozen")
    def study_is_frozen(sid):
        s = one("SELECT frozen, cutoff_date FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        return jsonify(frozen=bool(s["frozen"]), cutoff_date=s["cutoff_date"])
