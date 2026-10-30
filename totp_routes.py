"""2FA (TOTP) — setup, enable, disable, verify."""
from flask import (render_template, request, redirect, url_for,
                   flash, g, session, abort)
from werkzeug.security import check_password_hash
from database import one, execute
from totp import (gen_secret, verify_code, otpauth_url,
                  backup_codes, qr_png_b64)
from config import APP_NAME


def register(app):

    @app.route("/profile/2fa")
    def two_factor_page():
        u = one("SELECT * FROM users WHERE id=?", (g.user["id"],))
        return render_template("two_factor.html", u=u)

    @app.post("/profile/2fa/setup")
    def two_factor_setup():
        secret = gen_secret()
        session["_pending_totp"] = secret
        u = one("SELECT username FROM users WHERE id=?", (g.user["id"],))
        url = otpauth_url(secret, f"{APP_NAME}:{u['username']}", APP_NAME)
        qr = qr_png_b64(url)
        codes = backup_codes()
        session["_pending_backup_codes"] = codes
        return render_template("two_factor_setup.html",
                               secret=secret, qr=qr, url=url, codes=codes)

    @app.post("/profile/2fa/enable")
    def two_factor_enable():
        code = (request.form.get("code") or "").strip().replace(" ", "")
        secret = session.get("_pending_totp")
        codes = session.get("_pending_backup_codes", [])
        if not secret:
            flash("Setup expired. Start again.", "danger")
            return redirect(url_for("two_factor_page"))
        if not verify_code(secret, code):
            flash("Code did not match. Try again.", "danger")
            return redirect(url_for("two_factor_page"))
        execute("""UPDATE users SET totp_secret=?, totp_enabled=1,
                   totp_backup_codes=? WHERE id=?""",
                (secret, ",".join(codes), g.user["id"]))
        session.pop("_pending_totp", None)
        session.pop("_pending_backup_codes", None)
        try:
            execute("""INSERT INTO audit_log (user_id, action, target_type, target_id)
                       VALUES(?, '2FA_ENABLE', 'user', ?)""",
                    (g.user["id"], g.user["id"]))
        except Exception: pass
        flash("Two-factor authentication enabled.", "success")
        return redirect(url_for("two_factor_page"))

    @app.post("/profile/2fa/disable")
    def two_factor_disable():
        password = request.form.get("password", "")
        u = one("SELECT * FROM users WHERE id=?", (g.user["id"],))
        if not check_password_hash(u["password_hash"], password):
            flash("Password is incorrect.", "danger")
            return redirect(url_for("two_factor_page"))
        execute("""UPDATE users SET totp_secret='', totp_enabled=0,
                   totp_backup_codes='' WHERE id=?""", (g.user["id"],))
        try:
            execute("""INSERT INTO audit_log (user_id, action, target_type, target_id)
                       VALUES(?, '2FA_DISABLE', 'user', ?)""",
                    (g.user["id"], g.user["id"]))
        except Exception: pass
        flash("Two-factor disabled.", "warning")
        return redirect(url_for("two_factor_page"))

    @app.route("/login/2fa", methods=["GET", "POST"])
    def two_factor_verify():
        uid = session.get("_pending_2fa_user")
        if not uid:
            return redirect(url_for("login"))
        if request.method == "POST":
            code = (request.form.get("code") or "").strip().replace(" ", "").upper()
            u = one("SELECT * FROM users WHERE id=?", (uid,))
            if not u:
                session.pop("_pending_2fa_user", None)
                return redirect(url_for("login"))
            ok = False
            if u["totp_secret"] and verify_code(u["totp_secret"], code):
                ok = True
            else:
                backups = [c.strip().upper() for c in (u["totp_backup_codes"] or "").split(",") if c.strip()]
                if code in backups:
                    backups.remove(code)
                    execute("UPDATE users SET totp_backup_codes=? WHERE id=?",
                            (",".join(backups), u["id"]))
                    ok = True
            if ok:
                session.pop("_pending_2fa_user", None)
                session["user_id"] = u["id"]
                import secrets as _s
                session["_csrf"] = _s.token_urlsafe(32)
                execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (u["id"],))
                try:
                    execute("""INSERT INTO audit_log (user_id, action, target_type, target_id)
                               VALUES(?, 'LOGIN_2FA', 'user', ?)""", (u["id"], u["id"]))
                except Exception: pass
                return redirect(url_for("dashboard"))
            flash("Invalid code.", "danger")
        return render_template("two_factor_verify.html")
