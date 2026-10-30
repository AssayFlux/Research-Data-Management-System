"""Avatar system — pick, generate, upload. Available to every user."""
import os, secrets
from pathlib import Path
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from werkzeug.utils import secure_filename
from database import query, one, execute
from config import UPLOAD_DIR
from emoji_data import (EMOJI, DICEBEAR_STYLES, DICEBEAR_STYLE_LABELS,
                        GIF_TOPICS, all_emojis, search_emoji)

AVATAR_DIR = Path(UPLOAD_DIR) / "avatars"
ALLOWED_IMG = {".png",".jpg",".jpeg",".gif",".webp"}


def _ensure_avatar_dir():
    """Create the avatar folder lazily — avoids import-time side effects."""
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)


def register(app):
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

    # ─── Avatar picker ───
    @app.route("/profile/avatar")
    def avatar_picker():
        u = one("""SELECT id, username, role, avatar_type, avatar_value, avatar_style
                   FROM users WHERE id=?""", (g.user["id"],))
        return render_template("avatar_picker.html",
                               user=u,
                               emoji_catalog=EMOJI,
                               db_styles=DICEBEAR_STYLES,
                               db_labels=DICEBEAR_STYLE_LABELS,
                               gif_topics=GIF_TOPICS,
                               tab=request.args.get("tab", "initials"))

    # ─── Save avatar ───
    @app.post("/profile/avatar/save")
    def avatar_save():
        _ensure_avatar_dir()
        kind = request.form.get("kind", "initials")
        value = (request.form.get("value") or "").strip()
        style = (request.form.get("style") or "").strip()

        if kind == "initials":
            value = ""; style = ""
        elif kind == "emoji":
            if not value or len(value) > 10:
                flash("Pick an emoji.", "danger")
                return redirect(url_for("avatar_picker", tab="emoji"))
        elif kind == "dicebear":
            if style not in DICEBEAR_STYLES:
                style = "adventurer"
            if not value:
                value = secrets.token_hex(4)
        elif kind == "upload":
            f = request.files.get("file")
            if not f or not f.filename:
                flash("Choose an image file.", "danger")
                return redirect(url_for("avatar_picker", tab="upload"))
            ext = Path(f.filename).suffix.lower()
            if ext not in ALLOWED_IMG:
                flash(f"Image type '{ext}' not allowed.", "danger")
                return redirect(url_for("avatar_picker", tab="upload"))
            fname = f"u{g.user['id']}_{secrets.token_hex(4)}{ext}"
            f.save(str(AVATAR_DIR / fname))
            kind, value, style = "upload", fname, ""
        elif kind == "gif":
            if not (value.startswith("http://") or value.startswith("https://")):
                flash("Paste a full https:// image URL.", "danger")
                return redirect(url_for("avatar_picker", tab="gif"))
            style = ""
        else:
            kind, value, style = "initials", "", ""

        execute("""UPDATE users SET avatar_type=?, avatar_value=?, avatar_style=?
                   WHERE id=?""", (kind, value, style, g.user["id"]))
        audit("UPDATE", "avatar", g.user["id"], f"{kind}:{value[:40]}")
        flash("Avatar updated.", "success")
        return redirect(url_for("avatar_picker"))

    @app.route("/profile/avatar/reset", methods=["POST"])
    def avatar_reset():
        execute("""UPDATE users SET avatar_type='initials',
                   avatar_value='', avatar_style='' WHERE id=?""", (g.user["id"],))
        audit("RESET", "avatar", g.user["id"])
        flash("Avatar reset to initials.", "success")
        return redirect(url_for("avatar_picker"))

    # ─── Emoji search (used by picker JS) ───
    @app.post("/profile/avatar/emoji-search")
    def emoji_search():
        q = request.form.get("q", "")
        return jsonify(emojis=search_emoji(q)[:80],
                       total=len(all_emojis()))

    # ─── Uploaded avatar file server ───
    @app.route("/avatar/<path:fname>")
    def avatar_file(fname):
        from flask import send_from_directory
        return send_from_directory(str(AVATAR_DIR), fname)

    # ─── Random seed for DiceBear ───
    @app.route("/profile/avatar/random-seed")
    def avatar_random_seed():
        return jsonify(seed=secrets.token_hex(4))
