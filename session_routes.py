"""Multi-device session management."""
import secrets as _s
from flask import (render_template, request, redirect, url_for,
                   flash, g, session, abort)
from database import query, one, execute


def register(app):

    # Helper: record session on every login
    @app.before_request
    def _track_session():
        if not getattr(g, "user", None):
            return
        tok = session.get("_sess_tok")
        if not tok:
            tok = _s.token_urlsafe(24)
            session["_sess_tok"] = tok
            try:
                execute("""INSERT INTO user_sessions
                           (user_id, token, device, ip, user_agent)
                           VALUES(?,?,?,?,?)""",
                        (g.user["id"], tok,
                         request.user_agent.platform or "unknown",
                         request.remote_addr or "",
                         (request.user_agent.string or "")[:200]))
            except Exception:
                pass
            session["_sess_last_ping"] = 0
            return

        # Verify revocation once per request (cheap SELECT)
        try:
            row = one("SELECT revoked FROM user_sessions WHERE user_id=? AND token=?",
                      (g.user["id"], tok))
            if not row or row["revoked"]:
                session.clear()
                return
        except Exception:
            return

        # Update last_seen at most once per 60 seconds
        import time
        now_ts = int(time.time())
        last = session.get("_sess_last_ping", 0)
        if now_ts - last >= 60:
            try:
                execute("UPDATE user_sessions SET last_seen=CURRENT_TIMESTAMP "
                        "WHERE user_id=? AND token=? AND revoked=0",
                        (g.user["id"], tok))
                session["_sess_last_ping"] = now_ts
            except Exception:
                pass

    @app.route("/account/sessions")
    def account_sessions():
        rows = query("""SELECT * FROM user_sessions
                        WHERE user_id=? AND revoked=0
                        ORDER BY last_seen DESC""", (g.user["id"],))
        current = session.get("_sess_tok")
        return render_template("account_sessions.html", rows=rows, current=current)

    @app.post("/account/sessions/<int:sid>/revoke")
    def account_session_revoke(sid):
        s = one("SELECT * FROM user_sessions WHERE id=?", (sid,))
        if not s or s["user_id"] != g.user["id"]:
            abort(403)
        execute("UPDATE user_sessions SET revoked=1 WHERE id=?", (sid,))
        flash("Session revoked.", "success")
        return redirect(url_for("account_sessions"))

    @app.post("/account/sessions/revoke-others")
    def account_sessions_revoke_others():
        current = session.get("_sess_tok")
        execute("""UPDATE user_sessions SET revoked=1
                   WHERE user_id=? AND token != ?""", (g.user["id"], current))
        flash("All other sessions revoked.", "success")
        return redirect(url_for("account_sessions"))
