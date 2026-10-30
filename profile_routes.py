"""User profile — edit display name + email-ish fields."""
from flask import render_template, request, redirect, url_for, flash, g
from database import one, execute


def register(app):

    @app.route("/profile/edit", methods=["GET", "POST"])
    def profile_edit():
        u = one("""SELECT id, username, display_name, email, role, created_at, last_login
                   FROM users WHERE id=?""", (g.user["id"],))
        if not u:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            dn = (request.form.get("display_name") or "").strip()
            if len(dn) > 80:
                dn = dn[:80]
            if not dn:
                dn = u["username"]
            email = (request.form.get("email") or "").strip()[:120]
            if email and "@" not in email:
                flash("Please enter a valid email or leave blank.", "warning")
                email = u.get("email") or ""
            execute("UPDATE users SET display_name=?, email=? WHERE id=?",
                    (dn, email, u["id"]))
            try:
                execute("""INSERT INTO audit_log
                           (user_id, action, target_type, target_id, details)
                           VALUES(?, 'UPDATE_PROFILE', 'user', ?, ?)""",
                        (u["id"], u["id"], f"display_name={dn}"))
            except Exception:
                pass
            flash("Profile updated.", "success")
            return redirect(url_for("profile_edit"))

        return render_template("profile_edit.html", u=u)
