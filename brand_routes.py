"""Brand assets — site logo, favicon, login background. Admin only."""
import secrets
from pathlib import Path
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify, send_from_directory)
from werkzeug.utils import secure_filename
from database import one, execute, settings_dict, set_setting
from config import UPLOAD_DIR
from emoji_data import EMOJI
from brand_utils import resize_logo

BRAND_DIR = Path(UPLOAD_DIR) / "brand"
BRAND_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}


def register(app):
    def admin_required(fn):
        @wraps(fn)
        def w(*a, **kw):
            if not g.user or g.user["role"] != "ADMIN":
                abort(403)
            return fn(*a, **kw)
        return w

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

    def _save_upload(file_obj, prefix):
        """Save an uploaded image with auto-resize.
        Returns URL path or None."""
        if not file_obj or not file_obj.filename:
            return None
        ext = Path(file_obj.filename).suffix.lower()
        if ext not in ALLOWED_IMG:
            return None
        fname = f"{prefix}_{secrets.token_hex(4)}{ext}"
        dest = BRAND_DIR / fname

        # Save raw first
        tmp = BRAND_DIR / f"_tmp_{fname}"
        file_obj.save(str(tmp))

        # Auto-resize (SVG and ICO stay as-is)
        if ext in (".ico"):
            try:
                tmp.rename(dest)
            except Exception:
                import shutil
                shutil.move(str(tmp), str(dest))
        else:
            resize_logo(tmp, dest, max_width=600, max_height=600)
            try:
                tmp.unlink()
            except Exception:
                pass

        return url_for("brand_file", fname=fname)

    # ═══════════════════════════════════════════════════════
    # Brand settings page
    # ═══════════════════════════════════════════════════════
    @app.route("/admin/brand", methods=["GET", "POST"])
    @admin_required
    def brand_page():
        if request.method == "POST":
            section = request.form.get("section", "mark")

            if section == "mark":
                set_setting("brand_mark_type",
                            request.form.get("brand_mark_type", "emoji"))
                set_setting("brand_mark_value",
                            request.form.get("brand_mark_value", "✚"))

            elif section == "logos":
                # Brand logo
                url = _save_upload(request.files.get("brand_logo_file"),
                                    "brand_logo")
                if url is None:
                    url = request.form.get("brand_logo_url", "").strip()
                set_setting("brand_logo_url", url)

                # Favicon
                url = _save_upload(request.files.get("favicon_file"),
                                    "favicon")
                if url is None:
                    url = request.form.get("favicon_url", "").strip()
                set_setting("favicon_url", url)

                # Login logo
                url = _save_upload(request.files.get("login_logo_file"),
                                    "login_logo")
                if url is None:
                    url = request.form.get("login_logo_url", "").strip()
                set_setting("login_logo_url", url)

            elif section == "login_bg":
                set_setting("login_bg_type",
                            request.form.get("login_bg_type", "color"))
                set_setting("login_bg_value",
                            request.form.get("login_bg_value", "#f7f9fb"))

            audit("UPDATE", "brand", section)
            flash(f"Brand {section} saved.", "success")
            return redirect(url_for("brand_page"))

        s = settings_dict()
        return render_template("brand_page.html", s=s, emoji_catalog=EMOJI)

    # ═══════════════════════════════════════════════════════
    # Serve uploaded brand files
    # ═══════════════════════════════════════════════════════
    @app.route("/brand/<path:fname>")
    def brand_file(fname):
        # Security: block path traversal
        if ".." in fname or "/" in fname or "\\" in fname:
            abort(404)
        p = BRAND_DIR / fname
        if not p.exists():
            abort(404)
        return send_from_directory(str(BRAND_DIR), fname)
