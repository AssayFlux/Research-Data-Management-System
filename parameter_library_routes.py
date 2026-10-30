"""Parameter library — browse ~180 world-standard parameters, install into project."""
import sqlite3
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute, connect
from parameter_library import (LIBRARY, CATEGORIES, find, search,
                                by_category, by_tag, total)


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
                     action, ttype, str(tid), details, request.remote_addr or ""))
        except Exception:
            pass

    @app.route("/parameters/library")
    def parameter_library_page():
        q      = request.args.get("q", "").strip()
        cat    = request.args.get("cat", "").strip() or None
        tag    = request.args.get("tag", "").strip() or None
        if q:      items = search(q)
        elif tag:  items = by_tag(tag)
        else:      items = by_category(cat)
        # Which are already installed?
        installed_codes = {r["code"] for r in
                           query("SELECT code FROM parameters WHERE active=1")}
        return render_template("parameter_library.html",
                               items=items, q=q, cat=cat, tag=tag,
                               categories=CATEGORIES, total=total(),
                               installed_codes=installed_codes)

    @app.route("/parameters/library/<pid>")
    def parameter_library_detail(pid):
        p = find(pid)
        if not p: abort(404)
        existing = one("SELECT id FROM parameters WHERE code=?", (p["code"],))
        return render_template("parameter_library_detail.html",
                               p=p, installed=existing)

    @app.route("/parameters/library/<pid>/install", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def parameter_library_install(pid):
        p = find(pid)
        if not p: abort(404)

        if request.method == "POST":
            # Pick group name
            group_name = (request.form.get("group_name") or "").strip()
            gid = None
            if group_name:
                execute("INSERT OR IGNORE INTO parameter_groups(name) VALUES(?)", (group_name,))
                gid = one("SELECT id FROM parameter_groups WHERE name=?", (group_name,))["id"]

            try:
                new_id = execute("""INSERT INTO parameters
                    (code,name,group_id,category,data_type,unit,description,
                     ref_low,ref_high,ref_text,choices,min_value,max_value,
                     required,sort_order,formula)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (p["code"], p["name"], gid, p["category"],
                     p["data_type"], p["unit"] or "",
                     f"Installed from library · {p['subcategory']}",
                     p.get("ref_low"), p.get("ref_high"),
                     p.get("ref_text") or "", p.get("choices") or "",
                     None, None, 0, 0, ""))
                audit("INSTALL", "parameter", new_id, p["code"])
                flash(f"'{p['name']}' added to your project.", "success")
                return redirect(url_for("parameter_library_page"))
            except sqlite3.IntegrityError:
                flash(f"Parameter '{p['code']}' already exists in your project.", "danger")
                return redirect(url_for("parameter_library_detail", pid=pid))

        groups = query("SELECT name FROM parameter_groups ORDER BY name")
        return render_template("parameter_install.html", p=p, groups=groups)

    # ── Bulk install via checkboxes ──
    @app.post("/parameters/library/install-bulk")
    @role_required("ADMIN", "RESEARCHER")
    def parameter_library_install_bulk():
        picks = request.form.getlist("pick")
        if not picks:
            flash("Nothing selected.", "warning")
            return redirect(url_for("parameter_library_page"))
        group_name = (request.form.get("group_name") or "").strip()
        gid = None
        if group_name:
            execute("INSERT OR IGNORE INTO parameter_groups(name) VALUES(?)", (group_name,))
            gid = one("SELECT id FROM parameter_groups WHERE name=?", (group_name,))["id"]
        installed = 0
        c = connect()
        try:
            for pid in picks:
                p = find(pid)
                if not p: continue
                try:
                    c.execute("""INSERT INTO parameters
                        (code,name,group_id,category,data_type,unit,description,
                         ref_low,ref_high,ref_text,choices,min_value,max_value,
                         required,sort_order,formula)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (p["code"], p["name"], gid, p["category"],
                         p["data_type"], p["unit"] or "",
                         f"Installed from library · {p['subcategory']}",
                         p.get("ref_low"), p.get("ref_high"),
                         p.get("ref_text") or "", p.get("choices") or "",
                         None, None, 0, 0, ""))
                    installed += 1
                except sqlite3.IntegrityError:
                    pass  # already installed
        finally:
            c.close()
        audit("INSTALL_BULK", "parameter", "", f"{installed} params")
        flash(f"Installed {installed} parameters.", "success")
        return redirect(url_for("parameter_library_page"))
