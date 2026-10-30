"""File uploads per participant — safe, size-limited, audited."""
import os, secrets
from pathlib import Path
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, send_file)
from werkzeug.utils import secure_filename
from database import query, one, execute
from config import UPLOAD_DIR

ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp",
                ".pdf", ".txt", ".csv", ".doc", ".docx", ".xls", ".xlsx"}
MAX_FILE_MB = 25


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

    @app.route("/participant/<int:pid>/files")
    def files_list(pid):
        p = one("""SELECT p.*, s.study_code FROM participants p
                   JOIN studies s ON s.id = p.study_id WHERE p.id = ?""", (pid,))
        if not p: abort(404)
        rows = query("""SELECT * FROM participant_files
                        WHERE participant_id = ? ORDER BY id DESC""", (pid,))
        return render_template("files_list.html", p=p, rows=rows)

    @app.post("/participant/<int:pid>/files/upload")
    @role_required("ADMIN", "RESEARCHER")
    def files_upload(pid):
        if not one("SELECT id FROM participants WHERE id=?", (pid,)):
            abort(404)
        f = request.files.get("file")
        if not f or not f.filename:
            flash("Choose a file.", "danger")
            return redirect(url_for("files_list", pid=pid))
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_EXTS:
            flash(f"File type '{ext}' not allowed.", "danger")
            return redirect(url_for("files_list", pid=pid))
        f.stream.seek(0, os.SEEK_END)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > MAX_FILE_MB * 1024 * 1024:
            flash(f"File larger than {MAX_FILE_MB} MB.", "danger")
            return redirect(url_for("files_list", pid=pid))
        folder = Path(UPLOAD_DIR) / "participants" / str(pid)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = secrets.token_hex(6)
        safe = secure_filename(f.filename) or f"file{ext}"
        fname = f"{stamp}_{safe}"
        f.save(str(folder / fname))
        fid = execute("""INSERT INTO participant_files
            (participant_id, filename, original_name, mime, size)
            VALUES(?,?,?,?,?)""",
            (pid, fname, f.filename,
             f.mimetype or "application/octet-stream", size))
        audit("UPLOAD", "file", fid, f.filename)
        flash("File uploaded.", "success")
        return redirect(url_for("files_list", pid=pid))

    @app.route("/files/<int:fid>")
    def files_download(fid):
        row = one("SELECT * FROM participant_files WHERE id=?", (fid,))
        if not row: abort(404)
        path = Path(UPLOAD_DIR) / "participants" / str(row["participant_id"]) / row["filename"]
        if not path.exists(): abort(404)
        return send_file(str(path), as_attachment=False,
                         download_name=row["original_name"] or row["filename"],
                         mimetype=row["mime"] or "application/octet-stream")

    @app.route("/files/<int:fid>/download")
    def files_force_download(fid):
        row = one("SELECT * FROM participant_files WHERE id=?", (fid,))
        if not row: abort(404)
        path = Path(UPLOAD_DIR) / "participants" / str(row["participant_id"]) / row["filename"]
        if not path.exists(): abort(404)
        return send_file(str(path), as_attachment=True,
                         download_name=row["original_name"] or row["filename"])

    @app.post("/files/<int:fid>/delete")
    @role_required("ADMIN", "RESEARCHER")
    def files_delete(fid):
        row = one("SELECT * FROM participant_files WHERE id=?", (fid,))
        if not row: abort(404)
        path = Path(UPLOAD_DIR) / "participants" / str(row["participant_id"]) / row["filename"]
        try:
            if path.exists(): path.unlink()
        except Exception:
            pass
        execute("DELETE FROM participant_files WHERE id=?", (fid,))
        audit("DELETE", "file", fid)
        flash("File deleted.", "success")
        return redirect(url_for("files_list", pid=row["participant_id"]))
