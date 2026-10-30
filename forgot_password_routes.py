"""Forgot password — self-service reset via token, email optional."""
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, g, abort, current_app)
from werkzeug.security import generate_password_hash
from database import one, execute, query, setting, set_setting


TOKEN_TTL_MINUTES = 60


def _create_token(user_id, ip=""):
    """Invalidate old tokens, create a fresh one, return plain token."""
    execute("UPDATE password_resets SET used=1 WHERE user_id=? AND used=0", (user_id,))
    token = secrets.token_urlsafe(32)
    expires = (datetime.utcnow() + timedelta(minutes=TOKEN_TTL_MINUTES)).isoformat(sep=" ")
    execute("""INSERT INTO password_resets (user_id, token, expires_at, ip)
               VALUES(?,?,?,?)""", (user_id, token, expires, ip))
    return token


def _find_valid_token(token):
    """Return the reset row if the token is valid, else None."""
    row = one("""SELECT * FROM password_resets
                 WHERE token=? AND used=0""", (token,))
    if not row: return None
    try:
        exp = datetime.fromisoformat(row["expires_at"].replace(" ", "T"))
    except Exception:
        return None
    if datetime.utcnow() > exp:
        return None
    return row


def register(app):

    # ═══════════════════════════════════════════════════════
    # Self-service — step 1: request reset link
    # ═══════════════════════════════════════════════════════
    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if getattr(g, "user", None):
            return redirect(url_for("dashboard"))

        smtp_ready = False
        try:
            from email_helper import is_configured
            smtp_ready = is_configured()
        except Exception:
            smtp_ready = False

        if request.method == "POST":
            ident = (request.form.get("username") or "").strip()
            if not ident:
                flash("Enter your username or email.", "danger")
                return redirect(url_for("forgot_password"))

            # Match by username OR email
            u = one("""SELECT * FROM users
                       WHERE (username = ? OR email = ?) AND active = 1""",
                    (ident, ident))
            # Always show the same message, to not leak which users exist
            if not u:
                flash("If that account exists, a reset link has been sent.", "info")
                return redirect(url_for("login"))

            token = _create_token(u["id"], request.remote_addr or "")
            reset_url = url_for("reset_password_with_token", token=token, _external=True)

            # Try to send email if SMTP configured
            sent = False
            if smtp_ready and u["email"]:
                try:
                    from email_helper import send_now
                    body = (f"Hello {u['username']},\n\n"
                            f"Use this link to reset your password:\n\n{reset_url}\n\n"
                            f"The link expires in {TOKEN_TTL_MINUTES} minutes.\n\n"
                            f"If you didn't request this, ignore this email.\n")
                    ok, _ = send_now(u["email"], "Password reset", body)
                    sent = ok
                except Exception:
                    sent = False

            # If email not configured or couldn't send → show the link on the next page
            if not sent:
                flash(
                    f"Reset link generated. It expires in {TOKEN_TTL_MINUTES} minutes. "
                    f"Copy it now — it won't be shown again.",
                    "warning"
                )
                return render_template("forgot_password_link.html",
                                       reset_url=reset_url,
                                       username=u["username"],
                                       email=u["email"] or "",
                                       smtp_ready=smtp_ready)

            flash("If that account exists, a reset link has been sent.", "info")
            return redirect(url_for("login"))

        return render_template("forgot_password.html", smtp_ready=smtp_ready)

    # ═══════════════════════════════════════════════════════
    # Self-service — step 2: set new password
    # ═══════════════════════════════════════════════════════
    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password_with_token(token):
        row = _find_valid_token(token)
        if not row:
            flash("That reset link is invalid or has expired. "
                  "Please request a new one.", "danger")
            return redirect(url_for("forgot_password"))

        u = one("SELECT id, username FROM users WHERE id=?", (row["user_id"],))
        if not u:
            flash("Account no longer exists.", "danger")
            return redirect(url_for("forgot_password"))

        if request.method == "POST":
            p1 = request.form.get("new_password") or ""
            p2 = request.form.get("confirm_password") or ""

            if len(p1) < 8:
                flash("Password must be at least 8 characters.", "danger")
            elif p1 != p2:
                flash("Passwords do not match.", "danger")
            else:
                execute("UPDATE users SET password_hash=? WHERE id=?",
                        (generate_password_hash(p1, method="pbkdf2:sha256:260000"),
                         u["id"]))
                execute("UPDATE password_resets SET used=1 WHERE id=?", (row["id"],))
                try:
                    execute("""INSERT INTO audit_log
                               (user_id, action, target_type, target_id, details)
                               VALUES(?, 'PASSWORD_RESET_SELF', 'user', ?, 'via reset token')""",
                            (u["id"], u["id"]))
                except Exception:
                    pass
                flash("Password changed. You can now sign in.", "success")
                return redirect(url_for("login"))

        return render_template("reset_password.html", token=token, username=u["username"])

    # ═══════════════════════════════════════════════════════
    # Admin-triggered reset for another user
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/generate-reset-link")
    def users_generate_reset_link(uid):
        if not g.user or g.user["role"] != "ADMIN":
            abort(403)
        u = one("SELECT id, username, email FROM users WHERE id=?", (uid,))
        if not u: abort(404)
        token = _create_token(u["id"], request.remote_addr or "")
        reset_url = url_for("reset_password_with_token", token=token, _external=True)
        try:
            execute("""INSERT INTO audit_log
                       (user_id, action, target_type, target_id, details)
                       VALUES(?, 'PASSWORD_RESET_ADMIN', 'user', ?, ?)""",
                    (g.user["id"], uid, u["username"]))
        except Exception:
            pass
        flash(f"Reset link for '{u['username']}': {reset_url}", "success")
        return redirect(url_for("users_page"))
