"""Formula library — browse, compute standalone, install into project."""
import sqlite3
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute, connect
from formula import calculate, test_formula, substitute_codes
from formula_library import (LIBRARY, CATEGORIES, find, search, by_category)


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

    # ═════════════════════════════════════════════════
    # BROWSE
    # ═════════════════════════════════════════════════
    @app.route("/formulas/library")
    def formula_library_page():
        q    = request.args.get("q", "").strip()
        cat  = request.args.get("cat", "").strip() or None
        if q:
            items = search(q)
        else:
            items = by_category(cat)
        return render_template("formula_library.html",
                               items=items, q=q, cat=cat,
                               categories=CATEGORIES,
                               total=len(LIBRARY))

    @app.route("/formulas/library/<fid>")
    def formula_library_detail(fid):
        f = find(fid)
        if not f: abort(404)
        installed = one("""SELECT id FROM formulas WHERE code=?""", (fid,))
        return render_template("formula_library_detail.html",
                               f=f, installed=installed)

    # ═════════════════════════════════════════════════
    # STANDALONE COMPUTE
    # ═════════════════════════════════════════════════
    @app.post("/formulas/library/<fid>/compute")
    def formula_library_compute(fid):
        f = find(fid)
        if not f: return jsonify(error="Formula not found"), 404
        values = {}
        errors = []
        for inp in f["inputs"]:
            raw = request.form.get(inp["key"], "").strip()
            if raw == "":
                errors.append(f"{inp['label']} is required")
                continue
            try:
                values[inp["key"]] = float(raw)
            except ValueError:
                errors.append(f"{inp['label']} must be a number")
        if errors:
            return jsonify(error="; ".join(errors)), 400
        try:
            result = calculate(f["expression"], values)
            return jsonify(result=round(float(result), 6),
                           unit=f.get("unit", ""),
                           reference=f.get("reference", ""),
                           source=f.get("source", ""))
        except Exception as e:
            return jsonify(error=str(e)), 400

    # ═════════════════════════════════════════════════
    # INSTALL INTO PROJECT
    # ═════════════════════════════════════════════════
    @app.route("/formulas/library/<fid>/install", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def formula_library_install(fid):
        f = find(fid)
        if not f: abort(404)

        params = query("""SELECT id, code, name, unit, data_type
                          FROM parameters WHERE active=1
                          ORDER BY category, sort_order, name""")

        if request.method == "POST":
            # Map library input keys → parameter IDs
            mappings = {}
            for inp in f["inputs"]:
                pid = request.form.get(f"map_{inp['key']}") or ""
                if not pid:
                    flash(f"Please map input '{inp['label']}'.", "danger")
                    return redirect(url_for("formula_library_install", fid=fid))
                mappings[inp["key"]] = pid

            # Which parameter holds the output?
            out_pid = request.form.get("output_parameter_id") or ""
            if not out_pid:
                flash("Pick an output parameter.", "danger")
                return redirect(url_for("formula_library_install", fid=fid))

            # Build code-based expression
            id_to_code = {str(p["id"]): p["code"] for p in params}
            code_map = {k: id_to_code[v] for k, v in mappings.items()}
            try:
                new_expr = substitute_codes(f["expression"], code_map)
            except Exception as e:
                flash(f"Mapping failed: {e}", "danger")
                return redirect(url_for("formula_library_install", fid=fid))

            # Validate
            ok, res, names = test_formula(new_expr, {})
            if not ok and "Unknown variable" not in str(res):
                flash(f"Formula invalid after mapping: {res}", "danger")
                return redirect(url_for("formula_library_install", fid=fid))

            # Create the formulas row
            try:
                new_fid = execute("""INSERT INTO formulas
                    (name, code, expression, description, output_parameter_id)
                    VALUES(?,?,?,?,?)""",
                    (f["name"], f["id"], new_expr,
                     f.get("description", "")[:500], int(out_pid)))
                c = connect()
                try:
                    for inp in f["inputs"]:
                        c.execute("""INSERT OR IGNORE INTO formula_inputs
                                     (formula_id, parameter_id) VALUES(?,?)""",
                                  (new_fid, int(mappings[inp["key"]])))
                finally:
                    c.close()
                audit("INSTALL", "formula", new_fid, f["id"])
                flash(f"'{f['name']}' installed — it will auto-calculate "
                      f"on every data save from now on.", "success")
                return redirect(url_for("formulas_list"))
            except sqlite3.IntegrityError:
                flash(f"A formula with code '{f['id']}' is already installed.", "danger")
                return redirect(url_for("formula_library_detail", fid=fid))

        return render_template("formula_install.html", f=f, params=params)

    @app.post("/formulas/library/uninstall/<int:fid>")
    @role_required("ADMIN", "RESEARCHER")
    def formula_uninstall(fid):
        execute("DELETE FROM formulas WHERE id=?", (fid,))
        audit("UNINSTALL", "formula", fid)
        flash("Formula uninstalled.", "success")
        return redirect(url_for("formulas_list"))
