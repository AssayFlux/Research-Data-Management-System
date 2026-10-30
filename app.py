"""Biochemistry Research DMS — Flask app (Steps 1-3: auth, workspace, admin)."""
import secrets, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, abort, jsonify, g,
                   send_from_directory, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import (APP_NAME, APP_TAGLINE, SECRET_KEY, MAX_CONTENT_LENGTH,
                    PALETTE, ROLES, STATIC_DIR, DB_PATH, BACKUP_DIR,
                    DATA_TYPES)
from runtime_config import get_runtime
from database import (init_db, connect, query, one, execute, settings_dict,
                      setting, set_setting, json_load, revoke_user_sessions, visible_study_ids)
from formula import test_formula

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = timedelta(hours=12)  # overridden per-request by refresh_lifetime()
init_db()

# ============================================================
# CONTEXT
# ============================================================
@app.context_processor
def inject_globals():
    rt = get_runtime()
    return {
        "app_name":     setting("app_name", APP_NAME),
        "app_tagline":  setting("app_tagline", APP_TAGLINE),
        "institution":  setting("institution", ""),
        "app_settings": settings_dict(),
        "rt":           rt,                # ← runtime settings
        "palette":      PALETTE,
        "roles":        ROLES,
        "data_types":   DATA_TYPES,
        "now":          datetime.now(),
        "current_user": getattr(g, "user", None),
    }

# ============================================================
# AUTH GATE
# ============================================================
PUBLIC = {
    "brand_file",
    "avatar_file",
    "favicon",
    "forgot_password",
    "health",
    "health_check",
    "login",
    "manifest",
    "reset_password_with_token",
    "service_worker",
    "static",
    "two_factor_verify",
    "webauthn_has_credentials",
    "webauthn_login_begin",
    "webauthn_login_complete",
    "webauthn_register_begin",
    "webauthn_register_complete",
}

@app.before_request
def load_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        row = one("SELECT id,username,display_name,role,active,avatar_type,avatar_value,avatar_style FROM users WHERE id=? AND active=1", (uid,))
        if row:
            # A database-backed session token lets administrators/users revoke
            # a session immediately instead of waiting for cookie expiry.
            sess_tok = session.get("_sess_tok")
            if sess_tok:
                active_session = one(
                    "SELECT id FROM user_sessions WHERE user_id=? AND token=? AND revoked=0",
                    (uid, sess_tok),
                )
                if not active_session:
                    session.clear()
                    return None
            g.user = row
        else:
            session.clear()

@app.before_request
def require_login():
    ep = request.endpoint
    if not ep or ep in PUBLIC: return None
    if not g.user:
        return redirect(url_for("login", next=request.path))
    return None

def csrf_token():
    tok = session.get("_csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        session["_csrf"] = tok
    return tok
# ── Recent studies for sidebar quick actions ──
def recent_studies_for_sidebar(limit=3):
    try:
        from database import query
        return query("""SELECT id, study_code, title
                       FROM studies WHERE archived = 0
                       ORDER BY id DESC LIMIT ?""", (limit,))
    except Exception:
        return []

app.jinja_env.globals["recent_studies_for_sidebar"] = recent_studies_for_sidebar

def display_name_of(user):
    if not user:
        return ""
    try:
        dn = user["display_name"]
        if dn:
            return dn
    except (KeyError, IndexError, TypeError):
        pass
    try:
        return user["username"]
    except (KeyError, IndexError, TypeError):
        return ""

app.jinja_env.globals["display_name_of"] = display_name_of

app.jinja_env.globals["csrf_token"] = csrf_token

@app.context_processor
def _cache_buster():
    """Provides a token that changes every 10 seconds — forces browsers
    to fetch a fresh copy of any page that includes it in a URL."""
    import time
    return {"_cb": str(int(time.time() // 10))}



# ═══════════════════════════════════════════════════════════════
# ROLE ENFORCEMENT — central middleware (Phase 2.4)
# ═══════════════════════════════════════════════════════════════
ADMIN_ONLY_ENDPOINTS = {
    # User management
    "users_page", "user_edit", "user_toggle", "user_role", "user_delete",
    "user_reset_password", "user_generate_reset_link", "user_send_reset",
    # System administration
    "settings_page", "settings_ui_save", "audit_page", "health_check",
    "backups_page", "backup_create", "backup_download", "backup_delete",
    "brand_page", "email_settings", "email_queue_delete",
    # Print configuration (not data print)
    "print_settings", "print_preview", "print_reset",
    # Study governance
    "study_freeze",
    # Privacy-controlled export
    "deidentify_export",
}

# Endpoints a VIEWER may reach (read-only whitelist)
VIEWER_ALLOWED_ENDPOINTS = {
    "dashboard", "login", "logout", "static", "health", "favicon",
    "manifest", "service_worker",
    "profile_password", "profile_edit", "avatar_picker", "avatar_file",
    "avatar_random_seed", "emoji_search", "account_sessions",
    "studies_list",
    "parameters_list", "parameter_library_page", "parameter_library_detail",
    "forms_list", "form_view",
    "formulas_list", "formula_library_page", "formula_library_detail",
    "participants_list", "participant_detail",
    "records_list", "record_view", "record_history",
    "analysis_hub", "analysis_parameter_info", "analysis_descriptive",
    "analysis_normality", "analysis_compare", "analysis_multigroup",
    "analysis_correlate", "analysis_regression", "analysis_diagnostics",
    "analysis_forecast", "analysis_sample_size",
    "graphs_page", "graphs_data", "graphs_pair",
    "statistics_page", "statistics_describe", "statistics_compare",
    "statistics_correlate",
    "quality_page", "alerts_page",
    "visits_upcoming", "specimens_all", "adverse_list",
    "recruitment_page", "reliability_page", "reliability_compute",
    "longitudinal_page", "longitudinal_data",
    "print_hub", "print_participants_summary", "print_parameter_summary",
    "print_group_comparison", "print_study_progress", "print_quality_report",
    "print_blank_form", "print_statistics", "print_participant",
    "print_study", "print_records", "print_adverse_report",
    "export_page", "export_all", "export_study", "export_participant",
    "import_page",
    "data_dictionary_page", "data_dictionary_export",
    "learn_home", "learn_tab",
}


@app.before_request
def enforce_roles():
    """Central authorization. Runs after login and password enforcement."""
    if not getattr(g, "user", None):
        return None
    ep = request.endpoint or ""
    if not ep:
        return None
    # Public endpoints — no role check
    if ep in PUBLIC:
        return None
    role = g.user["role"]
    # ADMIN — full access
    if role == "ADMIN":
        return None
    # Non-admin: block admin-only endpoints
    if ep in ADMIN_ONLY_ENDPOINTS:
        abort(403)
    # VIEWER — read-only whitelist only
    if role == "VIEWER" and ep not in VIEWER_ALLOWED_ENDPOINTS:
        abort(403)
    # RESEARCHER — allowed on everything except admin-only
    return None


@app.before_request
def enforce_study_access():
    """Enforce study-level permissions for resource URLs and form mutations.

    ADMIN is unrestricted. Researchers/Viewers with explicit study assignments
    may only access records belonging to those studies. Legacy users with no
    assignments retain the existing unrestricted behaviour.
    """
    if not getattr(g, "user", None) or g.user["role"] == "ADMIN":
        return None

    from database import can_access_study
    ep = request.endpoint or ""
    va = request.view_args or {}

    # URL arguments whose IDs identify a study directly. Keep this list broad:
    # every route with a study-id URL must pass the same gate.
    direct_study_endpoints = {
        "study_edit", "study_archive", "study_permissions",
        "criteria_page", "criteria_reclassify_all",
        "study_freeze", "study_is_frozen", "classification_summary",
        "print_study", "print_participants_summary", "print_group_comparison",
        "print_study_progress", "print_statistics", "export_study",
        "study_archive_page", "study_archive_download",
    }
    if ep in direct_study_endpoints and "sid" in va:
        if not can_access_study(g.user, va["sid"]):
            abort(403)
        return None

    # URL arguments whose IDs resolve to a participant/record/etc.
    participant_eps = {
        "participant_detail", "participant_edit", "participant_archive",
        "data_new", "participant_reclassify", "participant_classification",
        "files_list", "files_upload", "print_participant", "export_participant",
        "participant_qr", "participant_qr_png", "print_quick_entry",
        "print_quick_entry_data", "print_quick_entry_qr",
        "participant_visits", "participant_visits_new",
        "participant_specimens", "participant_specimens_new",
    }
    if ep in participant_eps and "pid" in va:
        row = one("SELECT study_id FROM participants WHERE id=?", (va["pid"],))
        if not row or not can_access_study(g.user, row["study_id"]):
            abort(403)
        return None

    if ep in {"record_view", "record_edit", "record_lock", "record_unlock", "record_history"} and "rid" in va:
        row = one("""SELECT p.study_id FROM participant_records r
                     JOIN participants p ON p.id=r.participant_id WHERE r.id=?""",
                  (va["rid"],))
        if not row or not can_access_study(g.user, row["study_id"]):
            abort(403)
        return None

    if ep in {"adverse_edit", "adverse_resolve", "adverse_delete"} and "eid" in va:
        row = one("""SELECT p.study_id FROM adverse_events a
                     JOIN participants p ON p.id=a.participant_id WHERE a.id=?""",
                  (va["eid"],))
        if not row or not can_access_study(g.user, row["study_id"]):
            abort(403)
        return None

    if ep in {"quality_resolve"} and "qid" in va:
        row = one("""SELECT p.study_id FROM quality_checks q
                     JOIN participants p ON p.id=q.participant_id WHERE q.id=?""",
                  (va["qid"],))
        if not row or not can_access_study(g.user, row["study_id"]):
            abort(403)
        return None

    if ep in {"criteria_delete", "criteria_toggle"} and "cid" in va:
        row = one("SELECT study_id FROM criteria WHERE id=?", (va["cid"],))
        if row and row["study_id"] is not None and not can_access_study(g.user, row["study_id"]):
            abort(403)
        return None

    # Child resources must resolve back to a participant/study before access.
    child_study_queries = {
        "fid": "SELECT p.study_id FROM participant_files f JOIN participants p ON p.id=f.participant_id WHERE f.id=?",
        "vid": "SELECT p.study_id FROM visit_schedules v JOIN participants p ON p.id=v.participant_id WHERE v.id=?",
        "sid": "SELECT p.study_id FROM biospecimens sp JOIN participants p ON p.id=sp.participant_id WHERE sp.id=?",
        "aid": "SELECT p.study_id FROM alerts a JOIN participants p ON p.id=a.participant_id WHERE a.id=?",
    }
    for arg_name, sql in child_study_queries.items():
        if arg_name in va and ep not in {"study_edit", "study_archive", "study_permissions", "study_freeze", "study_is_frozen"}:
            row = one(sql, (va[arg_name],))
            if not row or not can_access_study(g.user, row["study_id"]):
                abort(403)
            return None

    # Any supplied study_id in query/form data is authoritative and must be
    # permitted. This closes IDORs on list, analysis, import and report routes.
    supplied_sid = request.args.get("study_id", type=int)
    if supplied_sid is None and request.method == "POST":
        raw = request.form.get("study_id")
        if raw not in (None, "", "0"):
            try:
                supplied_sid = int(raw)
            except (TypeError, ValueError):
                supplied_sid = None
    if supplied_sid is not None and not can_access_study(g.user, supplied_sid):
        abort(403)

    # POST forms such as /data/save identify the participant in the body.
    if request.method == "POST":
        pid = request.form.get("participant_id", type=int)
        if pid:
            row = one("SELECT study_id FROM participants WHERE id=?", (pid,))
            if not row or not can_access_study(g.user, row["study_id"]):
                abort(403)

    return None


@app.before_request
def enforce_password_change():
    """Force user to change password before any other action."""
    if not getattr(g, "user", None):
        return None
    ep = request.endpoint or ""
    # Allowed endpoints while password is pending
    ALLOWED = {
        "profile_password", "logout", "static", "health", "favicon",
    }
    # Check if user needs to change password
    try:
        row = one("SELECT must_change_password FROM users WHERE id=?",
                  (g.user["id"],))
        if row and row["must_change_password"]:
            if ep and ep not in ALLOWED:
                flash("Please change your password to continue.", "warning")
                return redirect(url_for("profile_password"))
    except Exception:
        pass
    return None


@app.before_request
def csrf_protect():
    ep = request.endpoint or ""
    if request.method == "POST" and ep not in ("login","health","health_check") and not ep.startswith("webauthn_"):
        sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("_csrf"):
            abort(400, "CSRF validation failed")

@app.after_request
def sec_headers(r):
    # Cache-busting: never let the browser serve a stale dashboard
    if r.mimetype in ("text/html", "text/css", "application/javascript", "text/javascript"):
        r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "SAMEORIGIN"
    r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # HSTS is only safe to advertise when the app is actually behind HTTPS.
    if request.is_secure:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return r

@app.before_request
def refresh_lifetime():
    if getattr(g, "user", None):
        rt = get_runtime()
        if session.get("remember"):
            app.permanent_session_lifetime = timedelta(days=rt["remember_days"])
        else:
            app.permanent_session_lifetime = timedelta(hours=rt["session_hours"])
        session.permanent = True

def audit(action, target_type="", target_id="", details=""):
    try:
        execute("INSERT INTO audit_log(user_id,action,target_type,target_id,details,ip) "
                "VALUES(?,?,?,?,?,?)",
                (getattr(g, "user", None)["id"] if getattr(g, "user", None) else None,
                 action, target_type, str(target_id), details, request.remote_addr or ""))
    except Exception: pass

def role_required(*roles):
    def deco(fn):
        @wraps(fn)
        def w(*a, **kw):
            if not g.user or g.user["role"] not in roles: abort(403)
            return fn(*a, **kw)
        return w
    return deco

def login_rate_ok(u, ip):
    rt = get_runtime()
    r = one("""SELECT COUNT(*) n FROM login_attempts
               WHERE (username=? OR ip=?) AND success=0
               AND attempted_at >= datetime('now', ?)""",
            (u, ip, f"-{rt['login_window_minutes']} minutes"))
    return (r["n"] or 0) < rt["login_max_attempts"]

def record_attempt(u, ip, ok):
    try:
        execute("INSERT INTO login_attempts(username,ip,success) VALUES(?,?,?)",
                (u, ip, 1 if ok else 0))
    except Exception: pass

# ============================================================
# AUTH ROUTES
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if getattr(g, "user", None): return redirect(url_for("dashboard"))
    if request.method == "POST":
        u  = (request.form.get("username") or "").strip()
        p  = request.form.get("password") or ""
        ip = request.remote_addr or ""
        if not login_rate_ok(u, ip):
            flash(f"Too many failed attempts. Try again later.", "danger")
            return render_template("login.html"), 429
        row = one("SELECT * FROM users WHERE username=? AND active=1", (u,))
        if row and check_password_hash(row["password_hash"], p):
            # ── 2FA branch ──
            try:
                totp_on = row["totp_enabled"]
            except (IndexError, KeyError):
                totp_on = 0
            if totp_on:
                session.clear()
                session["_pending_2fa_user"] = row["id"]
                return redirect(url_for("two_factor_verify"))
            session.clear()
            session["user_id"]  = row["id"]
            session["remember"] = bool(request.form.get("remember"))
            csrf_token()
            record_attempt(u, ip, True)
            execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
            audit("LOGIN", "user", row["id"])
            nxt = request.args.get("next") or url_for("dashboard")
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("dashboard")
            return redirect(nxt)
        record_attempt(u, ip, False)
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.post("/logout")
def logout():
    """Logout. Prefers POST with CSRF; GET supported for backwards compat."""
    if getattr(g, "user", None):
        try:
            audit("LOGOUT", "user", g.user["id"])
        except Exception:
            pass
    session.clear()
    return redirect(url_for("login"))

@app.route("/profile/password", methods=["GET", "POST"])
def profile_password():
    if request.method == "POST":
        cur  = request.form.get("current") or ""
        new  = request.form.get("new") or ""
        cf   = request.form.get("confirm") or ""
        u = one("SELECT * FROM users WHERE id=?", (g.user["id"],))
        if not check_password_hash(u["password_hash"], cur):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "danger")
        elif new != cf:
            flash("Passwords do not match.", "danger")
        else:
            execute(
                  "UPDATE users SET password_hash=?, must_change_password=0 WHERE id=?",
                  (generate_password_hash(new, method="pbkdf2:sha256:260000"), u["id"])
              )
            # Revoke other sessions
            try:
                _tok = session.get("_sess_tok")
                _n = revoke_user_sessions(u["id"], except_token=_tok)
                if _n: flash(f"Password changed. {_n} other session(s) signed out.", "success")
            except Exception: pass
            audit("CHANGE_PASSWORD", "user", u["id"])
            flash("Password changed.", "success")
            return redirect(url_for("dashboard"))
    return render_template("password.html")

# ============================================================
# DASHBOARD
# ============================================================
@app.route("/")
def dashboard():
    visible = visible_study_ids(g.user)
    study_clause = ""
    args = []
    if visible is not None:
        if not visible:
            study_clause = " AND 1=0"
        else:
            ph = ",".join("?" for _ in visible)
            study_clause = f" AND s.id IN ({ph})"
            args = list(visible)

    counts = {
        "studies": one("SELECT COUNT(*) n FROM studies s WHERE s.archived=0" + study_clause, args)["n"],
        "participants": one("SELECT COUNT(*) n FROM participants p JOIN studies s ON s.id=p.study_id WHERE p.archived=0" + study_clause, args)["n"],
        "parameters": one("SELECT COUNT(*) n FROM parameters WHERE active=1")["n"],
        "records": one("SELECT COUNT(*) n FROM participant_records r JOIN participants p ON p.id=r.participant_id JOIN studies s ON s.id=p.study_id WHERE 1=1" + study_clause, args)["n"],
        "users": one("SELECT COUNT(*) n FROM users WHERE active=1")["n"],
        "quality": one("SELECT COUNT(*) n FROM quality_checks q JOIN participants p ON p.id=q.participant_id JOIN studies s ON s.id=p.study_id WHERE q.resolved=0" + study_clause, args)["n"],
        "forms": one("SELECT COUNT(*) n FROM forms f LEFT JOIN studies s ON s.id=f.study_id WHERE 1=1" + study_clause, args)["n"],
        "formulas": one("SELECT COUNT(*) n FROM formulas WHERE active=1")["n"],
    }
    recent = query("""SELECT a.*, u.username FROM audit_log a
                      LEFT JOIN users u ON u.id=a.user_id
                      ORDER BY a.id DESC LIMIT 8""")
    return render_template("dashboard.html", counts=counts, recent=recent)

# ============================================================
# STUDIES
# ============================================================
@app.route("/studies")
def studies_list():
    visible = visible_study_ids(g.user)
    sql = """SELECT s.*, (SELECT COUNT(*) FROM participants p
                            WHERE p.study_id=s.id AND p.archived=0) AS n_participants
             FROM studies s WHERE s.archived=0"""
    args = []
    if visible is not None:
        if not visible:
            rows = []
            sql = None
        else:
            placeholders = ",".join("?" * len(visible))
            sql += f" AND s.id IN ({placeholders})"
            args = list(visible)
    else:
        pass
    if sql:
        sql += " ORDER BY s.id DESC"
        rows = query(sql, args)
    return render_template("studies.html", rows=rows)


@app.route("/studies/new", methods=["GET", "POST"])
@role_required("ADMIN", "RESEARCHER")
def study_new():
    if request.method == "POST":
        try:
            sid = execute("""INSERT INTO studies(study_code,title,description,pi,
                institution,department,protocol_no,ethics_no,start_date,end_date,
                status,sample_target) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (request.form["study_code"].strip(), request.form["title"].strip(),
                 request.form.get("description", ""), request.form.get("pi", ""),
                 request.form.get("institution", ""), request.form.get("department", ""),
                 request.form.get("protocol_no", ""), request.form.get("ethics_no", ""),
                 request.form.get("start_date") or None,
                 request.form.get("end_date") or None,
                 request.form.get("status", "ACTIVE"),
                 int(request.form.get("sample_target") or 0)))
            audit("CREATE", "study", sid, request.form["study_code"])
            flash("Study created.", "success")
            return redirect(url_for("studies_list"))
        except sqlite3.IntegrityError:
            flash("Study code already exists.", "danger")
    return render_template("study_form.html", row=None)

@app.route("/studies/<int:sid>/edit", methods=["GET", "POST"])
@role_required("ADMIN", "RESEARCHER")
def study_edit(sid):
    row = one("SELECT * FROM studies WHERE id=?", (sid,))
    if not row: abort(404)
    if request.method == "POST":
        try:
            execute("""UPDATE studies SET study_code=?,title=?,description=?,pi=?,
                institution=?,department=?,protocol_no=?,ethics_no=?,
                start_date=?,end_date=?,status=?,sample_target=? WHERE id=?""",
                (request.form["study_code"].strip(), request.form["title"].strip(),
                 request.form.get("description", ""), request.form.get("pi", ""),
                 request.form.get("institution", ""), request.form.get("department", ""),
                 request.form.get("protocol_no", ""), request.form.get("ethics_no", ""),
                 request.form.get("start_date") or None,
                 request.form.get("end_date") or None,
                 request.form.get("status", "ACTIVE"),
                 int(request.form.get("sample_target") or 0), sid))
            audit("UPDATE", "study", sid)
            flash("Study updated.", "success")
            return redirect(url_for("studies_list"))
        except sqlite3.IntegrityError:
            flash("Study code already exists.", "danger")
    return render_template("study_form.html", row=row)

@app.post("/studies/<int:sid>/archive")
@role_required("ADMIN", "RESEARCHER")
def study_archive(sid):
    execute("UPDATE studies SET archived=1 WHERE id=?", (sid,))
    audit("ARCHIVE", "study", sid)
    flash("Study archived.", "success")
    return redirect(url_for("studies_list"))

# ============================================================
# PARAMETERS
# ============================================================
@app.route("/parameters")
def parameters_list():
    q         = (request.args.get("q") or "").strip()
    category  = (request.args.get("category") or "").strip()
    group_id  = request.args.get("group_id") or ""

    # Build parameter query with optional filters
    sql = """SELECT p.*, g.name AS group_name
             FROM parameters p
             LEFT JOIN parameter_groups g ON g.id = p.group_id
             WHERE p.active = 1"""
    args = []

    if q:
        sql += " AND (p.code LIKE ? OR p.name LIKE ? OR g.name LIKE ?)"
        args += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND p.category = ?"
        args.append(category)
    if group_id:
        try:
            sql += " AND p.group_id = ?"
            args.append(int(group_id))
        except ValueError:
            pass

    sql += " ORDER BY p.sort_order, p.name"
    rows = query(sql, args)

    # Groups list — always unfiltered so the dropdown stays complete
    groups = query("""SELECT g.*,
                      (SELECT COUNT(*) FROM parameters p
                       WHERE p.group_id = g.id AND p.active = 1) AS n
                      FROM parameter_groups g ORDER BY g.sort_order, g.name""")

    return render_template("parameters.html", rows=rows, groups=groups)


@app.route("/parameters/new", methods=["GET", "POST"])
@role_required("ADMIN", "RESEARCHER")
def parameter_new():
    groups = query("SELECT * FROM parameter_groups ORDER BY sort_order, name")
    if request.method == "POST":
        try:
            gid = request.form.get("group_id") or None
            new_group = (request.form.get("new_group") or "").strip()
            if new_group:
                execute("INSERT OR IGNORE INTO parameter_groups(name) VALUES(?)", (new_group,))
                gid = one("SELECT id FROM parameter_groups WHERE name=?", (new_group,))["id"]
            pid = execute("""INSERT INTO parameters(code,name,group_id,category,
                data_type,unit,description,ref_low,ref_high,ref_text,choices,
                min_value,max_value,required,sort_order,formula)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (request.form["code"].strip(), request.form["name"].strip(),
                 gid, request.form.get("category", "Other"),
                 request.form.get("data_type", "Decimal"),
                 request.form.get("unit", ""), request.form.get("description", ""),
                 request.form.get("ref_low") or None,
                 request.form.get("ref_high") or None,
                 request.form.get("ref_text", ""), request.form.get("choices", ""),
                 request.form.get("min_value") or None,
                 request.form.get("max_value") or None,
                 1 if request.form.get("required") else 0,
                 int(request.form.get("sort_order") or 0),
                 request.form.get("formula", "")))
            audit("CREATE", "parameter", pid, request.form["code"])
            flash("Parameter created.", "success")
            return redirect(url_for("parameters_list"))
        except sqlite3.IntegrityError:
            flash("Parameter code already exists.", "danger")
    return render_template("parameter_form.html", row=None, groups=groups)

@app.route("/parameters/<int:pid>/edit", methods=["GET", "POST"])
@role_required("ADMIN", "RESEARCHER")
def parameter_edit(pid):
    row = one("SELECT * FROM parameters WHERE id=?", (pid,))
    if not row: abort(404)
    groups = query("SELECT * FROM parameter_groups ORDER BY sort_order, name")
    if request.method == "POST":
        try:
            execute("""UPDATE parameters SET code=?, name=?, group_id=?,
                category=?, data_type=?, unit=?, description=?, ref_low=?,
                ref_high=?, ref_text=?, choices=?, min_value=?, max_value=?,
                required=?, sort_order=?, formula=? WHERE id=?""",
                (request.form["code"].strip(), request.form["name"].strip(),
                 request.form.get("group_id") or None,
                 request.form.get("category", "Other"),
                 request.form.get("data_type", "Decimal"),
                 request.form.get("unit", ""), request.form.get("description", ""),
                 request.form.get("ref_low") or None,
                 request.form.get("ref_high") or None,
                 request.form.get("ref_text", ""), request.form.get("choices", ""),
                 request.form.get("min_value") or None,
                 request.form.get("max_value") or None,
                 1 if request.form.get("required") else 0,
                 int(request.form.get("sort_order") or 0),
                 request.form.get("formula", ""), pid))
            audit("UPDATE", "parameter", pid)
            flash("Parameter updated.", "success")
            return redirect(url_for("parameters_list"))
        except sqlite3.IntegrityError:
            flash("Parameter code already exists.", "danger")
    return render_template("parameter_form.html", row=row, groups=groups)

@app.post("/parameters/<int:pid>/archive")
@role_required("ADMIN", "RESEARCHER")
def parameter_archive(pid):
    execute("UPDATE parameters SET active=0 WHERE id=?", (pid,))
    audit("ARCHIVE", "parameter", pid)
    flash("Parameter archived.", "success")
    return redirect(url_for("parameters_list"))

@app.post("/parameters/group")
@role_required("ADMIN", "RESEARCHER")
def parameter_group_create():
    name = (request.form.get("name") or "").strip()
    if name:
        execute("INSERT OR IGNORE INTO parameter_groups(name) VALUES(?)", (name,))
        audit("CREATE", "parameter_group", "", name)
        flash(f"Group '{name}' created.", "success")
    return redirect(url_for("parameters_list"))

# ============================================================
# FORMS
# ============================================================
@app.route("/forms")
def forms_list():
    rows = query("""SELECT f.*, s.study_code,
                    (SELECT COUNT(*) FROM form_fields ff WHERE ff.form_id=f.id) AS field_count
                    FROM forms f LEFT JOIN studies s ON s.id=f.study_id
                    ORDER BY f.id DESC""")
    studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
    params = query("""SELECT id,code,name,category FROM parameters
                      WHERE active=1 ORDER BY category, sort_order, name""")
    return render_template("forms.html", rows=rows, studies=studies, params=params)

@app.post("/forms/new")
@role_required("ADMIN", "RESEARCHER")
def form_new():
    try:
        fid = execute("INSERT INTO forms(study_id,name,description,status) VALUES(?,?,?,?)",
                      (request.form.get("study_id") or None,
                       request.form["name"].strip(),
                       request.form.get("description", ""),
                       request.form.get("status", "DRAFT")))
        selected = request.form.getlist("parameter_ids")
        c = connect()
        try:
            for i, pid in enumerate(selected):
                c.execute("INSERT INTO form_fields(form_id,parameter_id,display_order) VALUES(?,?,?)",
                          (fid, int(pid), i))
        finally: c.close()
        audit("CREATE", "form", fid, request.form["name"])
        flash(f"Form created with {len(selected)} field(s).", "success")
    except Exception as e:
        flash(f"Could not create form: {e}", "danger")
    return redirect(url_for("forms_list"))

@app.route("/forms/<int:fid>")
def form_view(fid):
    form = one("""SELECT f.*, s.study_code, s.title AS study_title
                  FROM forms f LEFT JOIN studies s ON s.id=f.study_id WHERE f.id=?""", (fid,))
    if not form: abort(404)
    fields = query("""SELECT p.*, ff.section, ff.display_order
                      FROM form_fields ff JOIN parameters p ON p.id=ff.parameter_id
                      WHERE ff.form_id=? ORDER BY ff.display_order""", (fid,))
    return render_template("form_view.html", form=form, fields=fields)

@app.post("/forms/<int:fid>/delete")
@role_required("ADMIN", "RESEARCHER")
def form_delete(fid):
    execute("DELETE FROM forms WHERE id=?", (fid,))
    audit("DELETE", "form", fid)
    flash("Form deleted.", "success")
    return redirect(url_for("forms_list"))

# ============================================================
# FORMULAS
# ============================================================
@app.route("/formulas")
def formulas_list():
    rows = query("""SELECT f.*, p.name AS output_name, p.code AS output_code
                    FROM formulas f LEFT JOIN parameters p ON p.id=f.output_parameter_id
                    ORDER BY f.id DESC""")
    params = query("SELECT id,code,name FROM parameters WHERE active=1 ORDER BY name")
    return render_template("formulas.html", rows=rows, params=params)

@app.post("/formulas/new")
@role_required("ADMIN", "RESEARCHER")
def formula_new():
    name = (request.form.get("name") or "").strip()
    code = (request.form.get("code") or "").strip()
    expr = (request.form.get("expression") or "").strip()
    if not (name and code and expr):
        flash("Name, code and expression are required.", "danger")
        return redirect(url_for("formulas_list"))
    ok, result, names = test_formula(expr, {})
    if not ok and "Unknown variable" not in str(result):
        flash(f"Formula error: {result}", "danger")
        return redirect(url_for("formulas_list"))
    try:
        fid = execute("""INSERT INTO formulas(name,code,expression,description,output_parameter_id)
                        VALUES(?,?,?,?,?)""",
                      (name, code, expr, request.form.get("description", ""),
                       request.form.get("output_parameter_id") or None))
        audit("CREATE", "formula", fid, code)
        flash("Formula created.", "success")
    except sqlite3.IntegrityError:
        flash("Formula code already exists.", "danger")
    return redirect(url_for("formulas_list"))

@app.post("/formulas/<int:fid>/delete")
@role_required("ADMIN", "RESEARCHER")
def formula_delete(fid):
    execute("DELETE FROM formulas WHERE id=?", (fid,))
    audit("DELETE", "formula", fid)
    flash("Formula deleted.", "success")
    return redirect(url_for("formulas_list"))

# ============================================================
# STEP 3: ADMIN — SETTINGS, HEALTH, AUDIT, USERS, BACKUPS
# ============================================================
@app.route("/settings", methods=["GET", "POST"])
@role_required("ADMIN")
def settings_page():
    VALID = ("branding", "appearance", "text", "interface", "login", "security")

    if request.method == "POST":
        section = request.form.get("section", "branding")
        if section in ("ui", "ui-save"):
            section = "interface"
        if section not in VALID:
            section = "branding"

        # Always save every ui_* key
        for k, v in request.form.items():
            if k.startswith("ui_"):
                set_setting(k, v)

        # Map both old & new section names
        section_map = {
            "branding":   ["app_name","app_tagline","institution","department","copyright","brand_mark_type","brand_mark_value","brand_logo_url","favicon_url","login_logo_url"],
            "appearance": [
                "ui_primary","ui_primary_gradient",
                "ui_accent","ui_accent_gradient",
                "ui_page_bg","ui_page_bg_gradient",
                "card_bg","card_bg_gradient",
                                                                "topbar_bg","topbar_bg_gradient",
                                "sidebar_bg","sidebar_bg_gradient",
                "sidebar_text",
                "font_family","ui_font_class",
            ],
            "text":       [
                "text_color","heading_color","muted_color",
                "link_color","sidebar_text","topbar_text",
            ],
            "interface":  ["ui_sidebar_w","ui_font_size","ui_compact","ui_bg_opacity","ui_card_opacity"],
            "login":      ["login_title","login_subtitle","login_bg","login_bg_gradient"],
            "security":   ["session_hours","remember_days","login_max_attempts","login_window_minutes"],
        }
        allowed = section_map.get(section, [])

        for k in allowed:
            if k in request.form:
                set_setting(k, request.form.get(k, ""))
            elif k in ("allow_remember", "ui_compact"):
                set_setting(k, "0")

        try:
            audit("UPDATE", "settings", section)
        except Exception:
            pass
        flash(f"{section.title()} settings saved.", "success")
        return redirect(url_for("settings_page", section=section))

    section = request.args.get("section", "branding")
    # Accept every alias the templates may send
    if section in ("ui", "ui-save"):
        section = "interface"
    if section not in VALID:
        section = "branding"

    return render_template("settings.html",
                           settings=settings_dict(),
                           section=section)

@app.route("/health")
@role_required("ADMIN")
def health_check():
    c = connect()
    try:
        integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [r["name"] for r in
                  c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    finally:
        c.close()
    required = ["users", "settings", "studies", "study_users", "participants",
                "parameter_groups", "parameters", "forms", "form_fields",
                "participant_records", "participant_values", "formulas",
                "formula_inputs", "quality_checks", "adverse_events",
                "participant_files", "audit_log"]
    missing = [t for t in required if t not in tables]
    checks = [
        ("Database file exists",      DB_PATH.exists()),
        ("SQLite integrity OK",       integrity == "ok"),
        ("All required tables",       len(missing) == 0),
        ("Backup directory ready",    Path(BACKUP_DIR).exists()),
        ("Static directory ready",    Path(STATIC_DIR).exists()),
    ]
    return render_template("health.html",
                           checks=checks, missing=missing,
                           tables=sorted(tables), integrity=integrity,
                           db_path=str(DB_PATH), n_tables=len(tables))

@app.route("/audit")
@role_required("ADMIN")
def audit_page():
    action_filter = request.args.get("action", "").strip()
    if action_filter:
        rows = query("""SELECT a.*, u.username FROM audit_log a
                        LEFT JOIN users u ON u.id=a.user_id
                        WHERE a.action=? ORDER BY a.id DESC LIMIT 500""",
                     (action_filter,))
    else:
        rows = query("""SELECT a.*, u.username FROM audit_log a
                        LEFT JOIN users u ON u.id=a.user_id
                        ORDER BY a.id DESC LIMIT 500""")
    actions = [r["action"] for r in
               query("SELECT DISTINCT action FROM audit_log ORDER BY action")]
    return render_template("audit.html", rows=rows,
                           actions=actions, action_filter=action_filter)

@app.post("/users/<int:uid>/password")
@role_required("ADMIN")
def user_password_reset(uid):
    new = request.form.get("password") or ""
    if len(new) < 8:
        flash("Password must be at least 8 characters.", "danger")
    else:
        execute("UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(new, method="pbkdf2:sha256:260000"), uid))
        audit("RESET_PASSWORD", "user", uid)
        flash("Password reset.", "success")
    return redirect(url_for("users_page"))

@app.route("/backups")
@role_required("ADMIN")
def backups_page():
    Path(BACKUP_DIR).mkdir(exist_ok=True)
    rows = sorted(Path(BACKUP_DIR).glob("research_*.db"), reverse=True)
    return render_template("backups.html", rows=rows)

@app.post("/backups/create")
@role_required("ADMIN")
def backup_create():
    Path(BACKUP_DIR).mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(BACKUP_DIR) / f"research_{stamp}.db"
    src = connect()
    try:
        dst = sqlite3.connect(dest)
        src.backup(dst)
        dst.close()
    finally:
        src.close()
    audit("BACKUP", "database", dest.name)
    flash(f"Backup created: {dest.name}", "success")
    return redirect(url_for("backups_page"))

@app.route("/backups/<name>/download")
@role_required("ADMIN")
def backup_download(name):
    p = Path(BACKUP_DIR) / name
    if not p.exists() or not name.endswith(".db"): abort(404)
    return send_file(p, as_attachment=True, download_name=name)

@app.post("/backups/<name>/delete")
@role_required("ADMIN")
def backup_delete(name):
    p = Path(BACKUP_DIR) / name
    if p.exists() and name.startswith("research_") and name.endswith(".db"):
        p.unlink()
        audit("DELETE", "backup", name)
        flash("Backup deleted.", "success")
    return redirect(url_for("backups_page"))

# ============================================================
# UTIL
# ============================================================
@app.route("/favicon.ico")
def favicon():
    p = STATIC_DIR / "favicon.ico"
    return send_from_directory(STATIC_DIR, "favicon.ico") if p.exists() else ("", 204)



# ═══════════════════════════════════════════════════════════
# Phase 2.5 — Assign users to a study
# ═══════════════════════════════════════════════════════════
@app.route("/studies/<int:sid>/permissions", methods=["GET", "POST"])
@role_required("ADMIN")
def study_permissions(sid):
    s = one("SELECT * FROM studies WHERE id=?", (sid,))
    if not s:
        abort(404)

    if request.method == "POST":
        c = connect()
        try:
            c.execute("DELETE FROM study_users WHERE study_id=?", (sid,))
            for uid in request.form.getlist("user_id"):
                try:
                    c.execute("INSERT OR IGNORE INTO study_users(study_id,user_id) VALUES(?,?)",
                              (sid, int(uid)))
                except ValueError:
                    pass
        finally:
            c.close()
        audit("UPDATE", "study_permissions", sid, f"{len(request.form.getlist('user_id'))} user(s)")
        flash("Study permissions saved.", "success")
        return redirect(url_for("study_permissions", sid=sid))

    all_users = query("""SELECT id, username, display_name, role, active
                         FROM users WHERE active=1 AND role != 'ADMIN'
                         ORDER BY username""")
    assigned = {r["user_id"] for r in
                query("SELECT user_id FROM study_users WHERE study_id=?", (sid,))}
    return render_template("study_permissions.html",
                           s=s, users=all_users, assigned=assigned)


@app.errorhandler(400)
def e400(e): return render_template("error.html", code=400, message=str(e)), 400
@app.errorhandler(403)
def e403(e): return render_template("error.html", code=403,
    message="You do not have permission for this action."), 403
@app.errorhandler(404)
def e404(e): return render_template("error.html", code=404,
    message="The requested page was not found."), 404
@app.errorhandler(429)
def e429(e): return render_template("error.html", code=429,
    message="Too many requests. Please slow down."), 429
@app.errorhandler(500)
def e500(e): return render_template("error.html", code=500,
    message="Internal server error. Check the Termux console."), 500

# ---- Step routes registration ----

# ── Step routes ──
try:
    import step4_routes; step4_routes.register(app)
except ImportError: pass
try:
    import step5_routes; step5_routes.register(app)
except ImportError: pass
try:
    import step6_routes; step6_routes.register(app)
except ImportError: pass
try:
    import step7_routes; step7_routes.register(app)
except ImportError: pass
try:
    import step8_routes; step8_routes.register(app)
except ImportError: pass
try:
    from print_settings import get_profile as _gpp
    app.jinja_env.globals['print_cfg'] = _gpp
except ImportError: pass

# ─────── Avatar & brand modules ───────

# ── Formula library ──
try:
    import formula_library_routes
    formula_library_routes.register(app)
    print('[ok] formula_library loaded')
except Exception as _e:
    print('[warn] formula_library:', _e)

# ── Parameter library + criteria ──
try:
    import parameter_library_routes; parameter_library_routes.register(app)
    print('[ok] parameter_library loaded')
except Exception as _e: print('[warn] parameter_library:', _e)
try:
    import criteria_routes; criteria_routes.register(app)
    print('[ok] criteria loaded')
except Exception as _e: print('[warn] criteria:', _e)

# ── Analysis engine ──
try:
    import analysis_routes; analysis_routes.register(app)
    print('[ok] analysis loaded')
except Exception as _e:
    print('[warn] analysis:', _e)

# ── Advanced records ──

# ── Step 16 modules ──
for _name in ('totp_routes','data_dictionary_routes','deidentify_routes',
              'longitudinal_routes','recruitment_routes','freeze_routes',
              'reliability_routes'):
    try:
        __import__(_name).register(app)
        print(f'[ok] {_name} loaded')
    except Exception as _e:
        print(f'[warn] {_name}:', _e)

# ── Step 18 modules ──
for _name in ('bulk_routes','visit_routes','alert_routes',
              'archive_routes','session_routes','email_routes'):
    try:
        __import__(_name).register(app)
        print(f'[ok] {_name} loaded')
    except Exception as _e:
        print(f'[warn] {_name}:', _e)

# ── WebAuthn (fingerprint login) ──

# ── Dynamic UI CSS from settings ──
@app.route("/ui.css")
def ui_css():
    """Dynamic CSS — DB settings override palette defaults."""
    from flask import Response
    from runtime_config import get_runtime
    rt = get_runtime()
    primary = rt["ui_primary"] or PALETTE.get("primary", "#0f766e")
    accent  = rt["ui_accent"]  or PALETTE.get("accent",  "#14b8a6")
    bg      = rt["ui_page_bg"] or PALETTE.get("page_bg", "#f7f9fb")
    sw      = rt["ui_sidebar_w"] or "240"
    fs      = rt["ui_font_size"] or "14"
    cm      = rt["ui_compact"]
    css = f"""
:root {{
  --primary: {primary};
  --primary-hover: {primary};
  --accent: {accent};
  --bg: {bg};
  --sidebar-w: {sw}px;
  --font-size-base: {fs}px;
}}
body {{ font-size: var(--font-size-base) !important; }}
.sidebar {{ width: var(--sidebar-w) !important; }}
main {{ margin-left: var(--sidebar-w) !important; }}
.topbar {{ left: var(--sidebar-w) !important; }}
.appfoot {{ left: var(--sidebar-w) !important; }}
.btn.primary {{ background: var(--primary) !important; border-color: var(--primary) !important; }}
.btn.primary:hover {{ background: var(--primary-hover) !important; border-color: var(--primary-hover) !important; }}
a {{ color: var(--primary); }}
.sidebar nav a.active {{ color: var(--primary); }}
.kpi:hover .kpi-label, .kpi:hover .kpi-value {{ color: var(--primary); }}
@media (max-width: 900px) {{
  main {{ margin-left: 0 !important; }}
  .topbar {{ left: 0 !important; }}
  .appfoot {{ left: 0 !important; }}
  .sidebar {{ width: 275px !important; }}
}}
"""
    if cm:
        css += """
.content { padding: 14px 16px 24px 16px !important; }
.card { padding: 12px !important; }
.kpi, .stat-card { padding: 10px 12px !important; }
table th, table td { padding: 6px 10px !important; }
.sidebar nav a { height: 30px !important; font-size: 13px !important; }
"""
    return Response(css, mimetype="text/css")

# ── Profile ──

# Fallback settings saver — safe if primary route fails
@app.post("/settings/ui-save")
@role_required("ADMIN")
def settings_ui_save():
    for k, v in request.form.items():
        if k.startswith("ui_"):
            set_setting(k, v)
    flash("Interface settings saved.", "success")
    return redirect(url_for("settings_page", section="ui"))

# ── Forgot password ──

# ── User admin ──

# (removed redundant first extension loop — see _EXT_MODULES below)

# ───── Extension modules (single registration) ─────
_EXT_MODULES = (
    "records_advanced_routes",
    "avatar_routes",
    "brand_routes",
    "webauthn_routes",
    "profile_routes",
    "user_admin_routes",
    "forgot_password_routes",
    "learn_routes",
    "qr_routes",
    "files_routes",
    "adverse_routes",
)
for _mod in _EXT_MODULES:
    try:
        _m = __import__(_mod)
        _m.register(app)
        print(f'[ok] {_mod} loaded')
    except AssertionError:
        print(f'[skip] {_mod}: already registered')
    except Exception as _e:
        print(f'[warn] {_mod}: {_e}')

# ── Public endpoint: check for webauthn credentials ──



# ── Permanent delete of a parameter ──
@app.post("/parameters/<int:pid>/delete")
@role_required("ADMIN", "RESEARCHER")
def parameter_delete(pid):
    from database import one as _one, execute as _exec
    p = _one("SELECT id, code, name FROM parameters WHERE id=?", (pid,))
    if not p:
        abort(404)
    # Check if used in any record
    used = _one("""SELECT COUNT(*) AS n FROM participant_values WHERE parameter_id=?""",
                (pid,))["n"]
    if used > 0:
        flash(
            f"Cannot delete '{p['name']}' — it has {used} saved value(s). "
            "Archive it instead.", "danger"
        )
        return redirect(url_for("parameters_list"))
    # Check if used in formulas
    fmls = _one("""SELECT COUNT(*) AS n FROM formula_inputs WHERE parameter_id=?""",
                (pid,))["n"]
    if fmls > 0:
        flash(
            f"Cannot delete '{p['name']}' — it is used in {fmls} formula(s). "
            "Remove it from formulas first.", "danger"
        )
        return redirect(url_for("parameters_list"))
    try:
        _exec("DELETE FROM form_fields WHERE parameter_id=?", (pid,))
        _exec("DELETE FROM parameters WHERE id=?", (pid,))
        audit("DELETE", "parameter", pid, p["code"])
        flash(f"Parameter '{p['name']}' deleted permanently.", "success")
    except Exception as e:
        flash(f"Could not delete: {e}", "danger")
    return redirect(url_for("parameters_list"))



# ── Delete a parameter group ──
@app.post("/parameters/group/<int:gid>/delete")
@role_required("ADMIN", "RESEARCHER")
def parameter_group_delete(gid):
    from database import one as _one, execute as _exec
    g = _one("SELECT * FROM parameter_groups WHERE id=?", (gid,))
    if not g:
        abort(404)
    # Count parameters currently in this group
    n = _one("SELECT COUNT(*) AS n FROM parameters WHERE group_id=? AND active=1",
             (gid,))["n"]
    # Detach parameters (set group_id to NULL) then delete group
    _exec("UPDATE parameters SET group_id=NULL WHERE group_id=?", (gid,))
    _exec("DELETE FROM parameter_groups WHERE id=?", (gid,))
    try:
        audit("DELETE", "parameter_group", gid, g["name"])
    except Exception:
        pass
    flash(f"Group '{g['name']}' removed. {n} parameter(s) unassigned.", "success")
    return redirect(url_for("parameters_list"))

# ── Quick Entry ──
try:
    import quick_entry_routes; quick_entry_routes.register(app)
    print('[ok] quick_entry_routes loaded')
except Exception as _e: print('[warn] quick_entry_routes:', _e)

# ── Quick Entry print ──
try:
    import print_quick_entry_routes
    print_quick_entry_routes.register(app)
    print('[ok] print_quick_entry_routes loaded')
except Exception as _e:
    print('[warn] print_quick_entry_routes:', _e)


# ═══════════════════════════════════════════════════════════════
# DYNAMIC THEME STYLESHEET — loaded with cache-busting ?v=timestamp
# ═══════════════════════════════════════════════════════════════

@app.route("/theme.css")
def theme_css():
    """Serve the site theme as CSS, driven by DB settings."""
    from flask import Response
    from database import settings_dict
    s = settings_dict()

    def g(k, d=""):
        return s.get(k, d) or d

    # Read all colour settings
    primary       = g("ui_primary", "#059669")
    primary_g     = g("ui_primary_gradient", "")
    accent        = g("ui_accent", "#14b8a6")
    accent_g      = g("ui_accent_gradient", "")
    bg            = g("ui_page_bg", "#f7f9fb")
    bg_g          = g("ui_page_bg_gradient", "")
    card_bg       = g("card_bg", "#ffffff")
    card_g        = g("card_bg_gradient", "")
    text          = g("text_color", "#0f172a")
    heading       = g("heading_color", "#0f172a")
    muted         = g("muted_color", "#64748b")
    link_col      = g("link_color", "#059669")
    topbar_bg     = g("topbar_bg", "#ffffff")
    topbar_bg_g   = g("topbar_bg_gradient", "")
    topbar_text   = g("topbar_text", "#0f172a")
    side_bg       = g("sidebar_bg", "#ffffff")
    side_bg_g     = g("sidebar_bg_gradient", "")
    side_text     = g("sidebar_text", "#334155")
    font_family   = g("font_family", "Inter, system-ui, sans-serif")
    font_size     = g("ui_font_size", "14")
    sidebar_w     = g("ui_sidebar_w", "240")

    def bgv(solid, grad):
        return grad if grad and grad.strip() else solid

    # Build the CSS in one pass — uses concatenation instead of f-string to avoid brace escaping
    css = []
    css.append(":root {")
    css.append("  --primary: %s;"       % primary)
    css.append("  --primary-hover: %s;" % primary)
    css.append("  --accent: %s;"        % accent)
    css.append("  --link-color: %s;"    % primary)
    css.append("  --bg: %s;"            % bg)
    css.append("  --card-bg: %s;"       % card_bg)
    css.append("  --topbar-bg: %s;"     % topbar_bg)
    css.append("  --sidebar-bg: %s;"    % side_bg)
    css.append("  --table-head-bg: %s;" % "#f1f5f9")
    css.append("  --input-bg: %s;"      % card_bg)
    css.append("  --text: %s;"          % text)
    css.append("  --heading-color: %s;" % heading)
    css.append("  --body-color: %s;"    % text)
    css.append("  --muted: %s;"         % muted)
    css.append("  --card-text: %s;"     % text)
    css.append("  --btn-text: %s;"      % "#ffffff")
    css.append("  --topbar-text: %s;"   % topbar_text)
    css.append("  --topbar-sub: %s;"    % muted)
    css.append("  --sidebar-text: %s;"  % side_text)
    css.append("  --sidebar-icon: %s;"  % muted)
    css.append("  --sidebar-active-bg: %s;" % "#ecfdf5")
    css.append("  --font-family: %s;"   % font_family)
    css.append("  --font-size-base: %spx;" % font_size)
    css.append("  --sidebar-w: %spx;"   % sidebar_w)
    css.append("  --border: %s;"         % "#e5e9ef")
    css.append("}")

    # Fonts
    css.append("html, body { font-family: var(--font-family) !important; font-size: var(--font-size-base) !important; }")

    # Page background — only html and body
    bgbg = bgv(bg, bg_g)
    css.append("html, body { background: %s !important; min-height: 100vh; }" % bgbg)
    css.append("main, section.content { background: transparent !important; }")
    css.append(".dash-wrap { background: transparent !important; }")

    # Text — with optional gradient support
    css.append("h1, h2, h3, h4, h5, h6 { color: %s !important; }" % heading)
    css.append("body, p, span, li, td, th, dd, dt, blockquote, figcaption, label { color: %s !important; }" % text)
    css.append("a, a:visited { color: %s !important; }" % link_col)
    css.append(".muted, .tiny, small, .text-muted { color: %s !important; }" % muted)

    # Sidebar
    side_bg_v = bgv(side_bg, side_bg_g)
    css.append(".sidebar, .sb-nav, .sb-items, .sb-group, .quick-panel, .sb-account { background: %s !important; }" % side_bg_v)
    css.append(".sidebar nav a, .sb-items a, .sb-items a:visited { color: %s !important; }" % side_text)
    css.append(".sidebar nav a .sb-ic, .sb-items a .sb-ic, .sidebar nav a svg, .sb-items a svg { stroke: %s !important; }" % muted)
    css.append(".sidebar nav a.active, .sb-items a.active { color: %s !important; background: %s !important; }" % (primary, "#ecfdf5"))
    css.append(".sidebar nav a.active svg, .sb-items a.active svg { stroke: %s !important; }" % primary)
    css.append(".quick-title, .quick-study-code, .quick-empty { color: %s !important; }" % side_text)

    # Topbar
    topbar_bg_v = bgv(topbar_bg, topbar_bg_g)
    css.append(".topbar, header.topbar { background: %s !important; }" % topbar_bg_v)
    css.append(".topbar-title { color: %s !important; }" % topbar_text)
    css.append(".topbar-sub { color: %s !important; }" % muted)
    css.append(".uc-name { color: %s !important; }" % topbar_text)
    css.append(".uc-role { color: %s !important; }" % muted)
    css.append(".topbar .hamb svg, .topbar .iconbtn svg { stroke: %s !important; }" % topbar_text)

    # Cards — ONLY the .card and .m-card / .lib-card panels.
    # Dashboard tiles (.d-*) and status panels stay with their own built-in colours.
    card_bg_v = bgv(card_bg, card_g)
    css.append(".card, .m-card, .lib-card, .criteria-card, .learn-card, .crit-row, .set-head, .cat-block { background: %s !important; color: %s !important; }" % (card_bg_v, text))
    css.append(".card h1, .card h2, .card h3, .kpi-card b, .qa-item b, .sys-item b, .d-hero h1, .d-kpi-num, .d-qa-title, .d-sys-name { color: %s !important; }" % heading)
    css.append(".card p, .card small, .d-hero-greet, .d-hero-sub, .d-qa-sub, .d-sys-sub { color: %s !important; }" % text)

    # Forms
    css.append("input, select, textarea { background: %s !important; color: %s !important; border-color: %s !important; }" % (card_bg, text, "#e5e9ef"))
    css.append("input::placeholder, textarea::placeholder { color: %s !important; }" % muted)

    # Tables
    css.append("table thead th { background: %s !important; color: %s !important; }" % ("#f1f5f9", heading))
    css.append("table tbody td { color: %s !important; }" % text)

    # Buttons
    prim_v = bgv(primary, primary_g)
    css.append(".btn.primary, button.primary { background: %s !important; border-color: %s !important; color: %s !important; }" % (prim_v, primary, "#ffffff"))
    css.append(".btn:not(.primary):not(.danger) { background: %s !important; color: %s !important; border-color: %s !important; }" % (card_bg, text, "#e5e9ef"))

    # Tabs / accents
    css.append(".set-tabs a.active, .settings-tabs a.active, .analysis-tabs a.active, .chart-tabs a.active, .print-tabs a.active, .avatar-tabs a.active { background: %s !important; color: %s !important; }" % (primary, "#ffffff"))
    if accent_g:
        css.append(".badge.info, .pill.info { background: %s !important; color: #fff !important; }" % accent_g)
        css.append(".progress-fill, .bar-fill { background: %s !important; }" % accent_g)
    else:
        css.append(".badge.info, .pill.info { background: %s !important; color: #fff !important; }" % accent)
        css.append(".progress-fill, .bar-fill { background: %s !important; }" % accent)
    css.append(".progress-fill, .bar-fill { background: %s !important; }" % accent)

    # Footer
    css.append("footer.appfoot, footer.appfoot::before, footer.appfoot::after, .appfoot { background: transparent !important; border: 0 !important; box-shadow: none !important; content: none !important; color: %s !important; opacity: 0.55 !important; padding: 16px 20px 10px !important; margin: 0 !important; text-align: center !important; font-size: 11px !important; position: static !important; width: 100%% !important; }" % muted)

    # Layout
    css.append(".sidebar { width: %spx !important; }" % sidebar_w)
    css.append("main { margin-left: %spx !important; }" % sidebar_w)
    css.append(".topbar { left: %spx !important; }" % sidebar_w)
    css.append("@media (max-width: 900px) { main { margin-left: 0 !important; } .topbar { left: 0 !important; } .sidebar { width: 275px !important; } }")

    body = "\n".join(css)

    return Response(body, mimetype="text/css", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    })



if __name__ == "__main__":
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║   Biochemistry Research Data Management System       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print("  ✅ Server started")
    print()
    print("  ➤  Open in your phone's browser:")
    print()
    print("         http://localhost:5000")
    print()
    print("  ➤  Or on this same phone:")
    print()
    print("         http://127.0.0.1:5000")
    print()
    print("  💡 Use localhost for fingerprint login.")
    print("  ─────────────────────────────────────────────────")
    print("  Database:", DB_PATH)
    print("  Press Ctrl+C to stop.")
    print()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
