"""Full user administration — edit, toggle, reset, delete."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from werkzeug.security import generate_password_hash
from database import query, one, execute, revoke_user_sessions


def register(app):
    def admin_required(fn):
        @wraps(fn)
        def w(*a, **kw):
            if not g.user or g.user["role"] != "ADMIN":
                abort(403)
            return fn(*a, **kw)
        return w

    def audit(action, tid="", details=""):
        try:
            execute("""INSERT INTO audit_log (user_id,action,target_type,target_id,details,ip)
                       VALUES(?,?,'user',?,?,?)""",
                    (g.user["id"], action, str(tid), details,
                     request.remote_addr or ""))
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # Users list
    # ═══════════════════════════════════════════════════════
    @app.route("/users", methods=["GET", "POST"])
    @admin_required
    def users_page():
        if request.method == "POST":
            try:
                uid = execute("""INSERT INTO users
                    (username, password_hash, role, active, display_name, email)
                    VALUES(?,?,?,1,?,?)""",
                    (request.form["username"].strip(),
                     generate_password_hash(request.form["password"],
                                            method="pbkdf2:sha256:260000"),
                     request.form.get("role", "RESEARCHER"),
                     request.form.get("display_name", "").strip(),
                     request.form.get("email", "").strip()))
                audit("CREATE", uid, request.form["username"])
                flash("User created.", "success")
            except Exception as e:
                if "UNIQUE" in str(e):
                    flash("Username already exists.", "danger")
                else:
                    flash(f"Create failed: {e}", "danger")
            return redirect(url_for("users_page"))

        rows = query("""SELECT id, username, display_name, email, role, active,
                               created_at, last_login
                        FROM users ORDER BY id""")
        return render_template("users.html", rows=rows)

    # ═══════════════════════════════════════════════════════
    # Edit user
    # ═══════════════════════════════════════════════════════
    @app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
    @admin_required
    def user_edit(uid):
        u = one("SELECT * FROM users WHERE id=?", (uid,))
        if not u:
            abort(404)

        if request.method == "POST":
            username = (request.form.get("username") or "").strip()
            display_name = (request.form.get("display_name") or "").strip()
            email = (request.form.get("email") or "").strip()
            role = request.form.get("role", u["role"])
            active = 1 if request.form.get("active") else 0

            if not username:
                flash("Username is required.", "danger")
                return redirect(url_for("user_edit", uid=uid))
            if role not in ("ADMIN", "RESEARCHER", "VIEWER"):
                role = "RESEARCHER"

            # Guard: last admin cannot demote/deactivate/delete themselves
            if uid == g.user["id"]:
                if not active:
                    flash("You cannot deactivate your own account.", "danger")
                    return redirect(url_for("user_edit", uid=uid))
                if role != "ADMIN":
                    # Check if other admins exist
                    n_admins = one("""SELECT COUNT(*) n FROM users
                                      WHERE role='ADMIN' AND active=1 AND id != ?""",
                                   (uid,))["n"]
                    if n_admins == 0:
                        flash("You are the only active ADMIN. Promote another admin first.",
                              "danger")
                        return redirect(url_for("user_edit", uid=uid))

            try:
                execute("""UPDATE users SET username=?, display_name=?,
                           email=?, role=?, active=? WHERE id=?""",
                        (username, display_name, email, role, active, uid))
                audit("UPDATE", uid, f"username={username} role={role} active={active}")
                flash("User updated.", "success")
                return redirect(url_for("users_page"))
            except Exception as e:
                if "UNIQUE" in str(e):
                    flash("Username already taken.", "danger")
                else:
                    flash(f"Update failed: {e}", "danger")

        return render_template("user_edit.html", u=u)

    # ═══════════════════════════════════════════════════════
    # Toggle active
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/toggle")
    @admin_required
    def user_toggle(uid):
        if uid == g.user["id"]:
            flash("You cannot deactivate your own account.", "danger")
            return redirect(url_for("users_page"))

        u = one("SELECT active, role FROM users WHERE id=?", (uid,))
        if not u:
            abort(404)

        # If disabling an admin, ensure another active admin exists
        if u["active"] and u["role"] == "ADMIN":
            n = one("""SELECT COUNT(*) n FROM users
                       WHERE role='ADMIN' AND active=1 AND id != ?""", (uid,))["n"]
            if n == 0:
                flash("Cannot disable the only active ADMIN.", "danger")
                return redirect(url_for("users_page"))

        execute("UPDATE users SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",
                (uid,))
        # If disabling, revoke sessions
        if u["active"]:
            try:
                revoke_user_sessions(uid)
            except Exception: pass
        audit("TOGGLE", uid, f"active={(1 - (u['active'] or 0))}")
        flash("Status changed.", "success")
        return redirect(url_for("users_page"))

    # ═══════════════════════════════════════════════════════
    # Change role inline
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/role")
    @admin_required
    def user_role(uid):
        newrole = request.form.get("role")
        if newrole not in ("ADMIN", "RESEARCHER", "VIEWER"):
            flash("Invalid role.", "danger")
            return redirect(url_for("users_page"))

        # Guard: demoting the only admin
        if uid == g.user["id"] and newrole != "ADMIN":
            n = one("""SELECT COUNT(*) n FROM users
                       WHERE role='ADMIN' AND active=1 AND id != ?""", (uid,))["n"]
            if n == 0:
                flash("You are the only active ADMIN.", "danger")
                return redirect(url_for("users_page"))

        execute("UPDATE users SET role=? WHERE id=?", (newrole, uid))
        audit("ROLE", uid, newrole)
        flash("Role updated.", "success")
        return redirect(url_for("users_page"))

    # ═══════════════════════════════════════════════════════
    # Reset password (set directly)
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/reset-password")
    @admin_required
    def user_reset_password(uid):
        new = (request.form.get("new_password") or "").strip()
        if len(new) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return redirect(url_for("user_edit", uid=uid) if request.form.get("back") == "edit"
                            else url_for("users_page"))
        execute("UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(new, method="pbkdf2:sha256:260000"), uid))
        try:
            revoke_user_sessions(uid)
        except Exception: pass
        audit("RESET_PASSWORD", uid, "admin set new password")
        flash("Password updated.", "success")
        return redirect(url_for("user_edit", uid=uid) if request.form.get("back") == "edit"
                        else url_for("users_page"))

    # ═══════════════════════════════════════════════════════
    # Delete user
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/delete")
    @admin_required
    def user_delete(uid):
        if uid == g.user["id"]:
            flash("You cannot delete your own account.", "danger")
            return redirect(url_for("users_page"))

        u = one("SELECT username, role, active FROM users WHERE id=?", (uid,))
        if not u:
            abort(404)

        if u["role"] == "ADMIN" and u["active"]:
            n = one("""SELECT COUNT(*) n FROM users
                       WHERE role='ADMIN' AND active=1 AND id != ?""", (uid,))["n"]
            if n == 0:
                flash("Cannot delete the only active ADMIN.", "danger")
                return redirect(url_for("users_page"))

        execute("DELETE FROM users WHERE id=?", (uid,))
        audit("DELETE", uid, f"username={u['username']}")
        flash(f"User '{u['username']}' deleted.", "success")
        return redirect(url_for("users_page"))

    # ═══════════════════════════════════════════════════════
    # Generate reset link (fallback for forgot-password)
    # ═══════════════════════════════════════════════════════
    @app.post("/users/<int:uid>/reset-link")
    @admin_required
    def user_generate_reset_link(uid):
        u = one("SELECT id, username FROM users WHERE id=?", (uid,))
        if not u:
            abort(404)
        try:
            from forgot_password_routes import _create_token
            token = _create_token(u["id"], request.remote_addr or "")
            reset_url = url_for("reset_password_with_token", token=token, _external=True)
            audit("RESET_LINK", uid, u["username"])
            flash(f"Reset link for '{u['username']}': {reset_url}", "success")
        except Exception as e:
            flash(f"Could not generate link: {e}", "danger")
        return redirect(url_for("users_page"))
