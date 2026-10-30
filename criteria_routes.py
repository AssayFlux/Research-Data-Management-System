"""Criteria management + reclassification."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute
from criteria_engine import classify_participant

OPERATORS = [
    ("gt",        "greater than (>)"),
    ("gte",       "≥"),
    ("lt",        "<"),
    ("lte",       "≤"),
    ("eq",        "equals (=)"),
    ("neq",       "not equal (≠)"),
    ("between",   "between (a ≤ x ≤ b)"),
    ("in",        "is one of (comma list)"),
    ("not_in",    "is not one of"),
    ("contains",  "contains text"),
    ("not_contains", "does not contain"),
    ("yes",       "is Yes"),
    ("no",        "is No"),
    ("exists",    "has any value"),
    ("empty",     "is empty"),
]

KINDS = [
    ("inclusion", "Inclusion criteria",  "#059669"),
    ("exclusion", "Exclusion criteria",  "#dc2626"),
    ("control",   "Control group rules", "#2563eb"),
    ("study",     "Study / Case rules",  "#7c3aed"),
]


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

    # ── Manage criteria for a study ──
    @app.route("/criteria")
    @role_required("ADMIN", "RESEARCHER")
    def criteria_landing():
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("criteria_landing.html", studies=studies)

    @app.route("/criteria/<int:sid>", methods=["GET", "POST"])
    @role_required("ADMIN", "RESEARCHER")
    def criteria_for_study(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)

        if request.method == "POST":
            kind = request.form.get("kind")
            if kind not in ("inclusion","exclusion","control","study"):
                abort(400, "Invalid kind")
            cid = execute("""INSERT INTO criteria
                (study_id, kind, name, parameter_id, operator, value1, value2,
                 description, sort_order)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (sid, kind,
                 request.form.get("name", "").strip(),
                 request.form.get("parameter_id") or None,
                 request.form.get("operator", "eq"),
                 request.form.get("value1", ""),
                 request.form.get("value2", ""),
                 request.form.get("description", ""),
                 int(request.form.get("sort_order") or 0)))
            audit("CREATE", "criteria", cid, f"{kind}: {request.form.get('name')}")
            flash("Criterion added.", "success")
            return redirect(url_for("criteria_for_study", sid=sid))

        rules = query("""SELECT c.*, p.name AS pname, p.code AS pcode, p.unit
                         FROM criteria c
                         LEFT JOIN parameters p ON p.id = c.parameter_id
                         WHERE c.study_id=?
                         ORDER BY c.kind, c.sort_order, c.id""", (sid,))
        by_kind = {"inclusion":[], "exclusion":[], "control":[], "study":[]}
        for r in rules:
            by_kind[r["kind"]].append(r)
        params = query("""SELECT id,code,name,data_type,unit FROM parameters
                          WHERE active=1 ORDER BY category, sort_order, name""")
        return render_template("criteria.html",
                               s=s, by_kind=by_kind, params=params,
                               operators=OPERATORS, kinds=KINDS)

    @app.post("/criteria/delete/<int:cid>")
    @role_required("ADMIN", "RESEARCHER")
    def criteria_delete(cid):
        r = one("SELECT study_id FROM criteria WHERE id=?", (cid,))
        if not r: abort(404)
        execute("DELETE FROM criteria WHERE id=?", (cid,))
        audit("DELETE", "criteria", cid)
        flash("Criterion removed.", "success")
        return redirect(url_for("criteria_for_study", sid=r["study_id"]))

    @app.post("/criteria/toggle/<int:cid>")
    @role_required("ADMIN", "RESEARCHER")
    def criteria_toggle(cid):
        r = one("SELECT study_id, active FROM criteria WHERE id=?", (cid,))
        if not r: abort(404)
        execute("UPDATE criteria SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (cid,))
        return redirect(url_for("criteria_for_study", sid=r["study_id"]))

    # ── Reclassify everyone in a study ──
    @app.post("/criteria/<int:sid>/reclassify-all")
    @role_required("ADMIN", "RESEARCHER")
    def criteria_reclassify_all(sid):
        parts = query("SELECT id FROM participants WHERE study_id=? AND archived=0", (sid,))
        counts = {}
        for p in parts:
            cls, reason, _ = classify_participant(p["id"])
            execute("""UPDATE participants SET classification=?,
                       classification_reason=?, classified_at=CURRENT_TIMESTAMP
                       WHERE id=?""", (cls, reason, p["id"]))
            counts[cls] = counts.get(cls, 0) + 1
        audit("RECLASSIFY", "study", sid, str(counts))
        flash(f"Reclassified {len(parts)} participants: " +
              ", ".join(f"{k}={v}" for k, v in counts.items()), "success")
        return redirect(url_for("criteria_for_study", sid=sid))

    # ── Reclassify a single participant ──
    @app.post("/participants/<int:pid>/reclassify")
    @role_required("ADMIN", "RESEARCHER")
    def participant_reclassify(pid):
        cls, reason, _ = classify_participant(pid)
        execute("""UPDATE participants SET classification=?,
                   classification_reason=?, classified_at=CURRENT_TIMESTAMP
                   WHERE id=?""", (cls, reason, pid))
        audit("RECLASSIFY", "participant", pid, cls)
        flash(f"Classified as {cls}.", "success")
        return redirect(url_for("participant_detail", pid=pid))

    @app.post("/participants/<int:pid>/classification")
    @role_required("ADMIN", "RESEARCHER")
    def participant_set_classification(pid):
        cls = request.form.get("classification", "Undetermined")
        if cls not in ("Control","Study","Excluded","Undetermined"):
            abort(400, "Invalid classification")
        reason = request.form.get("reason", "manually set")
        execute("""UPDATE participants SET classification=?,
                   classification_reason=?, classified_at=CURRENT_TIMESTAMP
                   WHERE id=?""", (cls, reason, pid))
        audit("CLASSIFY", "participant", pid, cls)
        flash(f"Set to {cls}.", "success")
        return redirect(url_for("participant_detail", pid=pid))
