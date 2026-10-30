"""Email — SMTP config, test send, queue management."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from database import query, one, execute, settings_dict, set_setting
from email_helper import send_now, queue, flush_queue, is_configured


def register(app):
    def admin_required(fn):
        @wraps(fn)
        def w(*a, **kw):
            if not g.user or g.user["role"] != "ADMIN":
                abort(403)
            return fn(*a, **kw)
        return w

    @app.route("/admin/email", methods=["GET", "POST"])
    @admin_required
    def email_settings():
        if request.method == "POST":
            action = request.form.get("action", "save")
            if action == "save":
                for k in ("smtp_host","smtp_port","smtp_user","smtp_pass",
                          "smtp_from","smtp_tls"):
                    if k in request.form:
                        set_setting(k, request.form.get(k, ""))
                flash("Email settings saved.", "success")
            elif action == "test":
                to = request.form.get("test_to")
                if not to:
                    flash("Enter a test recipient.", "danger")
                else:
                    ok, msg = send_now(to, "RDM test email",
                                       "This is a test from your Research DMS.")
                    flash(f"Test {'sent to ' + to if ok else 'failed: ' + msg}",
                          "success" if ok else "danger")
            elif action == "flush":
                sent, failed = flush_queue()
                flash(f"Queue flushed — sent: {sent}, failed: {failed}",
                      "success" if failed == 0 else "warning")
            return redirect(url_for("email_settings"))
        s = settings_dict()
        q = query("""SELECT * FROM email_queue
                     ORDER BY id DESC LIMIT 100""")
        configured = is_configured()
        return render_template("email_settings.html", s=s, queue=q,
                               configured=configured)

    @app.post("/admin/email/queue/<int:qid>/delete")
    @admin_required
    def email_queue_delete(qid):
        execute("DELETE FROM email_queue WHERE id=?", (qid,))
        return redirect(url_for("email_settings"))

    # ── Template: send password reset link ──
    @app.route("/users/<int:uid>/send-reset", methods=["POST"])
    @admin_required
    def user_send_reset(uid):
        u = one("SELECT * FROM users WHERE id=?", (uid,))
        if not u: abort(404)
        # Simple: tell them to reset manually + queue message (no token generated)
        body = (f"Hello {u['username']},\n\n"
                f"An administrator has asked you to change your password. "
                f"Please log in and visit /profile/password.\n\n"
                f"— {g.user['username']}")
        queue(u["username"], "Password reset requested", body)
        flash(f"Password reset notice queued for {u['username']}.", "success")
        return redirect(url_for("users_page"))
