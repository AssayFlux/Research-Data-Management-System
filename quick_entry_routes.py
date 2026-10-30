"""Quick Entry — single-page rush-hour data entry for one participant."""
import os, secrets, json
from pathlib import Path
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, g, jsonify, abort)
from werkzeug.utils import secure_filename
from database import query, one, execute, connect
from validation import validate_value
from formula import calculate
from config import UPLOAD_DIR

ALLOWED_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_MB = 15


def _row_get(row, key, default=""):
    """Safe getter for sqlite3.Row objects."""
    try:
        if key in row.keys():
            v = row[key]
            return v if v is not None else default
    except Exception:
        pass
    return default




CATEGORY_COLOR = {
    "Demographic":    "blue",
    "Anthropometric": "violet",
    "Biochemical":    "amber",
    "Hematology":     "rose",
    "Coagulation":    "teal",
    "Endocrine":      "cyan",
    "Vitals":         "orange",
    "Urine":          "lime",
    "Clinical":       "slate",
    "Other":          "gray",
}


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

    # ═══════════════════════════════════════════════════════
    # MAIN PAGE
    # ═══════════════════════════════════════════════════════
    @app.route("/quick-entry")
    @role_required("ADMIN", "RESEARCHER")
    def quick_entry_page():
        studies = query("""SELECT id, study_code, title FROM studies
                           WHERE archived = 0 ORDER BY title""")
        if not studies:
            flash("Create a study first.", "warning")
            return redirect(url_for("study_new"))

        sid = request.args.get("study_id", type=int) or studies[0]["id"]
        study = one("SELECT * FROM studies WHERE id = ?", (sid,))
        if not study:
            abort(404)

        # All active parameters, grouped by category
        params = query("""SELECT * FROM parameters WHERE active = 1
                          ORDER BY category, sort_order, name""")
        grouped = []
        by_cat = {}
        for p in params:
            by_cat.setdefault(p["category"] or "Other", []).append(p)
        for cat in ("Demographic", "Anthropometric", "Biochemical",
                    "Hematology", "Coagulation", "Endocrine",
                    "Vitals", "Urine", "Clinical", "Other"):
            if cat in by_cat:
                grouped.append({
                    "category": cat,
                    "color": CATEGORY_COLOR.get(cat, "gray"),
                    "params": by_cat[cat],
                })
            by_cat.pop(cat, None)
        for cat, items in by_cat.items():
            grouped.append({"category": cat, "color": "gray", "params": items})

        # Criteria for this study, grouped by kind
        crit = query("""SELECT c.*, p.name AS pname, p.code AS pcode, p.unit
                        FROM criteria c
                        LEFT JOIN parameters p ON p.id = c.parameter_id
                        WHERE c.study_id = ? AND c.active = 1
                        ORDER BY c.kind, c.sort_order, c.id""", (sid,))
        by_kind = {"inclusion": [], "exclusion": [], "control": [], "study": []}
        for c in crit:
            by_kind.setdefault(c["kind"], []).append(c)

        # Active formulas
        formulas = query("""SELECT f.*, p.code AS out_code, p.name AS out_name
                            FROM formulas f
                            LEFT JOIN parameters p ON p.id = f.output_parameter_id
                            WHERE f.active = 1 ORDER BY f.name""")

        # Recent entries (last 10 participants for this study)
        recent = query("""SELECT p.*, s.study_code,
                          (SELECT COUNT(*) FROM participant_files pf
                           WHERE pf.participant_id = p.id) AS n_files
                          FROM participants p
                          JOIN studies s ON s.id = p.study_id
                          WHERE p.archived = 0 AND p.study_id = ?
                          ORDER BY p.id DESC LIMIT 10""", (sid,))

        saved_pid = request.args.get("saved", type=int)
        saved = None
        if saved_pid:
            saved = one("""SELECT p.*, s.study_code FROM participants p
                           JOIN studies s ON s.id = p.study_id
                           WHERE p.id = ?""", (saved_pid,))

        return render_template("quick_entry.html",
                               studies=studies, study=study, sid=sid,
                               grouped=grouped, by_kind=by_kind,
                               formulas=formulas, recent=recent,
                               saved=saved,
                               category_colors=CATEGORY_COLOR)

    # ═══════════════════════════════════════════════════════
    # SAVE — creates participant + record + values + formula
    #          + auto-classification + prescription upload
    # ═══════════════════════════════════════════════════════
    @app.post("/quick-entry/save")
    @role_required("ADMIN", "RESEARCHER")
    def quick_entry_save():
        sid = int(request.form["study_id"])
        code = (request.form.get("participant_code") or "").strip()
        if not code:
            flash("Participant ID is required.", "danger")
            return redirect(url_for("quick_entry_page", study_id=sid))

        # ─── 1. Create participant ───
        try:
            pid = execute("""INSERT INTO participants
                (study_id, participant_code, consent_status, visit_date,
                 sex, age, group_type, screening_status,
                 enrollment_status, notes)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (sid, code,
                 request.form.get("consent_status", "Pending"),
                 request.form.get("entry_date") or None,
                 request.form.get("sex", ""),
                 request.form.get("age") or None,
                 request.form.get("group_type", "Auto"),
                 request.form.get("screening_status", "Screened"),
                 request.form.get("enrollment_status", "Enrolled"),
                 request.form.get("notes", "")))
        except Exception as e:
            msg = str(e)
            if "UNIQUE" in msg:
                flash(f"Participant ID '{code}' already exists in this study.", "danger")
            else:
                flash(f"Could not save participant: {e}", "danger")
            return redirect(url_for("quick_entry_page", study_id=sid))

        # ─── 2. Create record ───
        rid = execute("""INSERT INTO participant_records
                         (participant_id, visit_date, created_by)
                         VALUES(?,?,?)""",
                      (pid, request.form.get("entry_date") or None, g.user["id"]))

        # ─── 3. Save parameter values + collect numeric for formulas ───
        params = query("SELECT * FROM parameters WHERE active=1 ORDER BY sort_order, name")
        values = {}
        for p in params:
            raw = request.form.get(f"p_{p['id']}", "")
            text, num, state, err = validate_value(p, raw)
            execute("""INSERT INTO participant_values
                       (record_id, parameter_id, value_text, numeric_value, value_state)
                       VALUES(?,?,?,?,?)""",
                    (rid, p["id"], text, num, state))
            if num is not None and p["code"]:
                values[p["code"]] = num

        # ─── 4. Auto-formulas ───
        formulas = query("SELECT * FROM formulas WHERE active=1")
        for f in formulas:
            try:
                res = calculate(f["expression"], values)
                if f["output_parameter_id"]:
                    execute("""INSERT INTO participant_values
                               (record_id, parameter_id, numeric_value, value_state)
                               VALUES(?,?,?,'VALUE')
                               ON CONFLICT(record_id,parameter_id)
                               DO UPDATE SET numeric_value=excluded.numeric_value""",
                            (rid, f["output_parameter_id"], float(res)))
            except Exception:
                pass

        # ─── 5. Classification ───
        manual = (request.form.get("group_type") or "").strip()
        if manual in ("Study", "Control", "Excluded", "Undetermined"):
            execute("""UPDATE participants SET classification=?,
                       classification_reason='manually set',
                       classified_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (manual, pid))
        else:
            try:
                from criteria_engine import classify_participant
                cls, reason, _ = classify_participant(pid)
                execute("""UPDATE participants SET classification=?,
                           classification_reason=?, classified_at=CURRENT_TIMESTAMP
                           WHERE id=?""", (cls, reason, pid))
            except Exception:
                pass

        # ─── 6. Prescription upload ───
        f = request.files.get("prescription")
        if f and f.filename:
            ext = Path(f.filename).suffix.lower()
            if ext in ALLOWED_IMAGE:
                f.stream.seek(0, os.SEEK_END)
                size = f.stream.tell()
                f.stream.seek(0)
                if size <= MAX_MB * 1024 * 1024:
                    folder = Path(UPLOAD_DIR) / "participants" / str(pid)
                    folder.mkdir(parents=True, exist_ok=True)
                    fname = f"rx_{secrets.token_hex(4)}{ext}"
                    f.save(str(folder / fname))
                    execute("""INSERT INTO participant_files
                        (participant_id, filename, original_name, mime, size)
                        VALUES(?,?,?,?,?)""",
                        (pid, fname, f.filename,
                         f.mimetype or "application/octet-stream", size))

        try:
            execute("""INSERT INTO audit_log
                       (user_id, action, target_type, target_id, details)
                       VALUES(?, 'QUICK_ENTRY', 'participant', ?, ?)""",
                    (g.user["id"], str(pid), code))
        except Exception:
            pass

        flash(f"✓ Participant {code} saved.", "success")
        return redirect(url_for("quick_entry_page", study_id=sid, saved=pid))

    # ═══════════════════════════════════════════════════════
    # LIVE PREVIEW — classification + formulas
    # ═══════════════════════════════════════════════════════
    @app.post("/quick-entry/preview")
    @role_required("ADMIN", "RESEARCHER")
    def quick_entry_preview():
        sid = int(request.form.get("study_id") or 0)

        # Collect values from form
        vals = {}
        params = query("SELECT id, code FROM parameters WHERE active=1")
        for p in params:
            raw = request.form.get(f"p_{p['id']}", "")
            if raw == "":
                continue
            try:
                vals[p["id"]] = float(raw)
            except (ValueError, TypeError):
                vals[p["id"]] = raw

        # Evaluate criteria for this study
        crit = query("""SELECT * FROM criteria
                        WHERE study_id = ? AND active = 1""", (sid,))
        by_kind = {"inclusion": [], "exclusion": [], "control": [], "study": []}
        for c in crit:
            by_kind.setdefault(c["kind"], []).append(c)

        def check(rule):
            actual = vals.get(rule["parameter_id"])
            if actual is None:
                return None  # missing
            op = rule["operator"]
            try:
                a = float(actual)
                v1 = float(rule["value1"]) if rule["value1"] else None
                v2 = float(rule["value2"]) if rule["value2"] else None
            except (ValueError, TypeError):
                a = v1 = v2 = None

            if op == "gt":  return a is not None and v1 is not None and a > v1
            if op == "gte": return a is not None and v1 is not None and a >= v1
            if op == "lt":  return a is not None and v1 is not None and a < v1
            if op == "lte": return a is not None and v1 is not None and a <= v1
            if op == "eq":  return str(actual) == str(rule["value1"])
            if op == "neq": return str(actual) != str(rule["value1"])
            if op == "between":
                return a is not None and v1 is not None and v2 is not None and v1 <= a <= v2
            if op == "in":
                return str(actual) in [x.strip() for x in (rule["value1"] or "").split(",")]
            if op == "not_in":
                return str(actual) not in [x.strip() for x in (rule["value1"] or "").split(",")]
            if op == "yes":  return str(actual).lower() in ("yes","1","true")
            if op == "no":   return str(actual).lower() in ("no","0","false")
            if op == "exists": return actual not in (None, "")
            if op == "empty":  return actual in (None, "")
            return None

        inc_results = [check(r) for r in by_kind["inclusion"]]
        exc_results = [check(r) for r in by_kind["exclusion"]]
        ctrl_results = [check(r) for r in by_kind["control"]]
        study_results = [check(r) for r in by_kind["study"]]

        suggested = "Undetermined"
        reason = "Not enough data"

        if by_kind["inclusion"] and False in inc_results:
            failed = [r["name"] for r, v in zip(by_kind["inclusion"], inc_results) if v is False]
            suggested = "Excluded"
            reason = "Failed inclusion: " + ", ".join(failed[:3])
        elif by_kind["exclusion"] and True in exc_results:
            met = [r["name"] for r, v in zip(by_kind["exclusion"], exc_results) if v is True]
            suggested = "Excluded"
            reason = "Met exclusion: " + ", ".join(met[:3])
        elif by_kind["control"] and all(v is True for v in ctrl_results):
            suggested = "Control"
            reason = "All control rules met"
        elif by_kind["study"] and all(v is True for v in study_results):
            suggested = "Study"
            reason = "All study rules met"
        elif not any([by_kind["inclusion"], by_kind["exclusion"], by_kind["control"], by_kind["study"]]):
            suggested = "Undetermined"
            reason = "No criteria defined for this study"

        # Live formula calculations
        code_vals = {}
        for p in query("SELECT id, code FROM parameters"):
            if p["id"] in vals and isinstance(vals[p["id"]], (int, float)):
                code_vals[p["code"]] = vals[p["id"]]

        calc_results = []
        for f in query("""SELECT f.*, p.code AS out_code, p.name AS out_name, p.unit
                          FROM formulas f
                          LEFT JOIN parameters p ON p.id = f.output_parameter_id
                          WHERE f.active = 1"""):
            try:
                r = calculate(f["expression"], code_vals)
                calc_results.append({
                    "name": f["name"],
                    "code": f["out_code"] or f["code"],
                    "unit": f["unit"] or "",
                    "value": round(float(r), 3),
                    "ok": True,
                })
            except Exception:
                # Not enough inputs — skip
                calc_results.append({
                    "name": f["name"],
                    "code": f["out_code"] or f["code"],
                    "unit": f["unit"] or "",
                    "value": None,
                    "ok": False,
                })

        return jsonify({
            "classification": suggested,
            "reason": reason,
            "criteria": {
                "inclusion_passed": inc_results.count(True),
                "inclusion_total": len(by_kind["inclusion"]),
                "exclusion_triggered": exc_results.count(True),
                "exclusion_total": len(by_kind["exclusion"]),
                "control_passed": ctrl_results.count(True),
                "control_total": len(by_kind["control"]),
                "study_passed": study_results.count(True),
                "study_total": len(by_kind["study"]),
            },
            "calculations": calc_results,
        })

    # ═══════════════════════════════════════════════════════
    # SIDEBAR HELPER — count of studies (for badge)
    # ═══════════════════════════════════════════════════════
    @app.context_processor
    def inject_quick_entry():
        def recent_studies(limit=3):
            try:
                return query("""SELECT id, study_code, title FROM studies
                                WHERE archived = 0 ORDER BY id DESC LIMIT ?""",
                             (limit,))
            except Exception:
                return []
        return {"quick_entry_recent_studies": recent_studies}
