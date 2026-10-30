"""Step 7 — Print settings CRUD, preview, native print."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from database import execute
from print_settings import (CONTEXTS, DEFAULT_PROFILE,
                            get_profile, save_profile, list_profiles)


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

    def _parse_form(form):
        cfg = dict(DEFAULT_PROFILE)
        cfg["institution"] = form.get("institution", "").strip()
        cfg["subtitle"]    = form.get("subtitle", "").strip()
        cfg["department"]  = form.get("department", "").strip()
        cfg["study_name"]  = form.get("study_name", "").strip()
        cfg["logo_url"]    = form.get("logo_url", "").strip()
        cfg["copyright"]   = form.get("copyright", "").strip()
        cfg["website"]     = form.get("website", "").strip()
        cfg["extra_title"] = form.get("extra_title", "").strip() or "Additional notes"
        cfg["extra_content"] = form.get("extra_content", "")
        cfg["layout"]      = form.get("layout", "portrait")
        cfg["show_logo"]        = bool(form.get("show_logo"))
        cfg["show_signatures"]  = bool(form.get("show_signatures"))
        cfg["extra_enabled"]    = bool(form.get("extra_enabled"))
        cfg["show_page_numbers"] = bool(form.get("show_page_numbers"))
        try:
            cfg["margin_mm"] = max(5, min(40, int(form.get("margin_mm", "15"))))
        except (TypeError, ValueError):
            cfg["margin_mm"] = 15

        def collect(field):
            return [x.strip() for x in form.getlist(field) if x.strip()]

        cfg["header_lines"] = collect("header_line")
        cfg["guides"]       = collect("guide")
        cfg["coguides"]     = collect("coguide")
        cfg["researchers"]  = collect("researcher")
        cfg["signatures"]   = collect("signature")
        cfg["footer_lines"] = collect("footer_line")
        return cfg

    @app.route("/print/settings", methods=["GET", "POST"])
    @role_required("ADMIN")
    def print_settings():
        if request.method == "POST":
            profile = request.form.get("profile", "default")
            if profile not in CONTEXTS:
                profile = "default"
            save_profile(profile, _parse_form(request.form))
            audit("UPDATE", "print_settings", profile)
            flash(f"Print settings saved — {CONTEXTS[profile]}.", "success")
            return redirect(url_for("print_settings", profile=profile))

        profile = request.args.get("profile", "default")
        if profile not in CONTEXTS:
            profile = "default"
        return render_template("print_settings.html",
                               cfg=get_profile(profile),
                               profile=profile,
                               contexts=CONTEXTS,
                               profiles=list_profiles())

    @app.route("/print/preview")
    @role_required("ADMIN")
    def print_preview():
        profile = request.args.get("profile", "default")
        if profile not in CONTEXTS:
            profile = "default"
        return render_template("print_preview.html",
                               cfg=get_profile(profile), profile=profile)

    @app.route("/print/reset/<profile>", methods=["POST"])
    @role_required("ADMIN")
    def print_reset(profile):
        if profile not in CONTEXTS:
            profile = "default"
        save_profile(profile, dict(DEFAULT_PROFILE))
        audit("RESET", "print_settings", profile)
        flash(f"Profile reset — {CONTEXTS[profile]}.", "success")
        return redirect(url_for("print_settings", profile=profile))
