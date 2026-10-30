"""Step 4 — Participants, Records, Dynamic Data Collection routes."""
import sqlite3
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from database import query, one, execute, visible_study_ids, can_access_study
from validation import validate_value

CATEGORY_ORDER = ("Demographic", "Anthropometric", "Biochemical",
                  "Haematology", "Clinical", "Other")


def _group_by_category(rows):
    buckets = {}
    for row in rows:
        cat = row["category"] or "Other"
        buckets.setdefault(cat, []).append(row)
    ordered = []
    for cat in CATEGORY_ORDER:
        if cat in buckets:
            ordered.append((cat, buckets.pop(cat)))
    for cat in sorted(buckets):
        ordered.append((cat, buckets[cat]))
    return ordered


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

    # ---------------- PARTICIPANTS ----------------
    @app.route("/participants")
    def participants_list():
        study_id = request.args.get("study_id")
        q = (request.args.get("q") or "").strip()
        sql = """SELECT p.*, s.study_code, s.title AS study_title
                 FROM participants p
                 JOIN studies s ON s.id = p.study_id
                 WHERE p.archived = 0"""
        args = []
        if study_id:
            sql += " AND p.study_id = ?"; args.append(study_id)
        if q:
            sql += " AND (p.participant_code LIKE ? OR p.group_type LIKE ?)"
            args += [f"%{q}%", f"%{q}%"]
        sql += " ORDER BY p.id DESC LIMIT 500"
        rows = query(sql, args)
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        return render_template("participants.html", rows=rows, studies=studies)

    @app.route("/participants/new", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def participant_new():
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        if not studies:
            flash("Create a study first.", "warning")
            return redirect(url_for("study_new"))
        if request.method == "POST":
            sid = int(request.form["study_id"])
            code = request.form["participant_code"].strip()
            try:
                pid = execute("""INSERT INTO participants
                    (study_id, participant_code, consent_status, visit_date,
                     sex, age, group_type, screening_status,
                     enrollment_status, notes)
                    VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (sid, code,
                     request.form.get("consent_status", "Pending"),
                     request.form.get("visit_date") or None,
                     request.form.get("sex", ""),
                     request.form.get("age") or None,
                     request.form.get("group_type", "Unclassified"),
                     request.form.get("screening_status", "Screened"),
                     request.form.get("enrollment_status", "Enrolled"),
                     request.form.get("notes", "")))
                audit("CREATE", "participant", pid, code)
                flash("Participant created.", "success")
                return redirect(url_for("participant_detail", pid=pid))
            except sqlite3.IntegrityError:
                flash(f"Participant ID '{code}' already exists in this "
                      "study. Please use a different ID.", "danger")
        return render_template("participant_form.html", row=None, studies=studies)

    @app.route("/participants/<int:pid>")
    def participant_detail(pid):
        p = one("""SELECT p.*, s.study_code, s.title AS study_title
                   FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)
        records = query("""SELECT r.*, u.username
                           FROM participant_records r
                           LEFT JOIN users u ON u.id = r.created_by
                           WHERE r.participant_id = ?
                           ORDER BY r.id DESC""", (pid,))
        return render_template("participant_detail.html", p=p, records=records)

    @app.route("/participants/<int:pid>/edit", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def participant_edit(pid):
        row = one("SELECT * FROM participants WHERE id = ?", (pid,))
        if not row: abort(404)
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        if request.method == "POST":
            try:
                execute("""UPDATE participants SET
                    study_id=?, participant_code=?, consent_status=?,
                    visit_date=?, sex=?, age=?, group_type=?,
                    screening_status=?, enrollment_status=?, notes=?
                    WHERE id=?""",
                    (int(request.form["study_id"]),
                     request.form["participant_code"].strip(),
                     request.form.get("consent_status", "Pending"),
                     request.form.get("visit_date") or None,
                     request.form.get("sex", ""),
                     request.form.get("age") or None,
                     request.form.get("group_type", "Unclassified"),
                     request.form.get("screening_status", "Screened"),
                     request.form.get("enrollment_status", "Enrolled"),
                     request.form.get("notes", ""), pid))
                audit("UPDATE", "participant", pid)
                flash("Participant updated.", "success")
                return redirect(url_for("participant_detail", pid=pid))
            except sqlite3.IntegrityError:
                flash("Participant ID already exists in this study.", "danger")
        return render_template("participant_form.html", row=row, studies=studies)

    @app.post("/participants/<int:pid>/archive")
    @role_required("ADMIN", "RESEARCHER")
    def participant_archive(pid):
        execute("UPDATE participants SET archived = 1 WHERE id = ?", (pid,))
        audit("ARCHIVE", "participant", pid)
        flash("Participant archived.", "success")
        return redirect(url_for("participants_list"))

    # ---------------- DATA COLLECTION ----------------
    @app.route("/data/<int:pid>/new", methods=["GET"])
    @role_required("ADMIN", "RESEARCHER")
    def data_new(pid):
        p = one("""SELECT p.*, s.study_code FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)
        params = query("""SELECT * FROM parameters WHERE active = 1
                          ORDER BY sort_order, name""")
        grouped = _group_by_category(params)
        return render_template("data_collection.html", p=p, grouped=grouped)

    @app.post("/data/save")
    @role_required("ADMIN", "RESEARCHER")
    def data_save():
        pid = int(request.form["participant_id"])
        visit_date = request.form.get("visit_date") or None
        if not one("SELECT id FROM participants WHERE id = ?", (pid,)):
            abort(404)
        rid = execute("""INSERT INTO participant_records
                         (participant_id, visit_date, created_by)
                         VALUES(?,?,?)""",
                      (pid, visit_date, g.user["id"]))
        params = query("""SELECT * FROM parameters WHERE active = 1
                          ORDER BY sort_order, name""")
        warnings = []
        saved = 0
        for p in params:
            raw = request.form.get(f"p_{p['id']}", "")
            text, num, state, err = validate_value(p, raw)
            if err:
                warnings.append(f"{p['name']}: {err}")
                state = "MISSING"; text = None; num = None
            execute("""INSERT INTO participant_values
                       (record_id, parameter_id, value_text,
                        numeric_value, value_state)
                       VALUES(?,?,?,?,?)""",
                    (rid, p["id"], text, num, state))
            if state == "VALUE": saved += 1
        audit("CREATE", "record", rid, f"participant={pid} saved={saved}")
        # Evaluate alerts
        try:
            from alerts_engine import evaluate_record
            n_alerts = evaluate_record(rid)
            if n_alerts:
                flash(f"⚠️ {n_alerts} critical alert(s) triggered — see Alerts page.", "warning")
        except Exception:
            pass

        # Auto-classify
        try:
            from criteria_engine import classify_participant
            cls, reason, _ = classify_participant(pid)
            execute("""UPDATE participants SET classification=?, classification_reason=?, classified_at=CURRENT_TIMESTAMP WHERE id=?""", (cls, reason, pid))
        except Exception:
            pass
        if warnings:
            flash("Saved with warnings: " + " | ".join(warnings[:3]), "warning")
        else:
            flash(f"Record saved ({saved} values).", "success")
        return redirect(url_for("participant_detail", pid=pid))

    # ---------------- RECORDS ----------------
    @app.route("/records")
    def records_list():
        rows = query("""SELECT r.*, p.participant_code,
                               s.study_code, u.username
                        FROM participant_records r
                        JOIN participants p ON p.id = r.participant_id
                        JOIN studies s ON s.id = p.study_id
                        LEFT JOIN users u ON u.id = r.created_by
                        ORDER BY r.id DESC LIMIT 500""")
        return render_template("records.html", rows=rows)

    @app.route("/records/<int:rid>")
    def record_view(rid):
        r = one("""SELECT r.*, p.participant_code, p.id AS pid,
                          s.study_code, u.username
                   FROM participant_records r
                   JOIN participants p ON p.id = r.participant_id
                   JOIN studies s ON s.id = p.study_id
                   LEFT JOIN users u ON u.id = r.created_by
                   WHERE r.id = ?""", (rid,))
        if not r: abort(404)
        vals = query("""SELECT v.*, pa.name AS pname, pa.code AS pcode,
                               pa.unit, pa.category, pa.data_type,
                               pa.ref_low, pa.ref_high, pa.ref_text
                        FROM participant_values v
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE v.record_id = ?
                        ORDER BY pa.sort_order, pa.name""", (rid,))
        grouped = _group_by_category(vals)
        return render_template("record_view.html", r=r, grouped=grouped)
