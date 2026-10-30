"""Step 8 — 7 additional print profiles + Print center hub."""
import io, base64
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g)
from database import query, one, execute
from print_settings import get_profile
from statistics import descriptive, normality_test, compare_groups


def _chart_png_b64(kind, data, title=""):
    """Return base64 data URI for a chart, or None if matplotlib missing."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6.5, 3.2), dpi=110)
        if kind == "hist":
            if not data:
                plt.close(fig); return None
            ax.hist(data, bins=min(15, max(5, len(data))),
                    color="#059669", edgecolor="white")
            ax.set_xlabel("Value"); ax.set_ylabel("Frequency")
        elif kind == "bar_group":
            if not data:
                plt.close(fig); return None
            names = list(data.keys())
            vals = [(sum(v) / len(v) if v else 0) for v in data.values()]
            bars = ax.bar(names, vals, color="#059669")
            ax.set_ylabel("Mean value")
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}",
                        ha="center", va="bottom", fontsize=9)
        elif kind == "scatter":
            xs, ys = data
            ax.scatter(xs, ys, color="#059669", s=22)
            ax.set_xlabel("X"); ax.set_ylabel("Y")
        else:
            plt.close(fig); return None
        if title:
            ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3, linestyle=":")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def _values_for(parameter_id, study_id=None):
    sql = """SELECT v.numeric_value, v.value_state,
                    p.group_type, p.participant_code, p.id AS pid
             FROM participant_values v
             JOIN participant_records r ON r.id = v.record_id
             JOIN participants p ON p.id = r.participant_id
             WHERE v.parameter_id = ?"""
    args = [parameter_id]
    if study_id:
        sql += " AND p.study_id = ?"; args.append(study_id)
    return query(sql, args)


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

    # ==============================================================
    # PRINT CENTER (hub)
    # ==============================================================
    @app.route("/print")
    def print_hub():
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        params = query("""SELECT id,code,name,category FROM parameters
                          WHERE active=1 ORDER BY category, sort_order, name""")
        return render_template("print_hub.html", studies=studies, params=params)

    # ==============================================================
    # 1. PARTICIPANTS SUMMARY
    # ==============================================================
    @app.route("/print/participants-summary/<int:sid>")
    def print_participants_summary(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        parts = query("""SELECT * FROM participants
                         WHERE study_id=? AND archived=0
                         ORDER BY participant_code""", (sid,))
        groups = {}
        for p in parts:
            g = p["group_type"] or "Unclassified"
            groups[g] = groups.get(g, 0) + 1
        ages = [p["age"] for p in parts if p["age"] is not None]
        age_stats = descriptive(ages) if ages else {"n": 0}

        param_id = request.args.get("parameter_id", type=int)
        param = None
        param_values = {}
        if param_id:
            param = one("SELECT * FROM parameters WHERE id=?", (param_id,))
            rows = query("""SELECT v.numeric_value, v.value_text, v.value_state,
                                   p.id AS pid
                            FROM participant_values v
                            JOIN participant_records r ON r.id=v.record_id
                            JOIN participants p ON p.id=r.participant_id
                            WHERE p.study_id=? AND v.parameter_id=?""",
                         (sid, param_id))
            for r in rows:
                param_values[r["pid"]] = (r["numeric_value"]
                                          if r["numeric_value"] is not None
                                          else r["value_text"])

        return render_template("print_participants_summary.html",
                               s=s, parts=parts, groups=groups,
                               age_stats=age_stats,
                               param=param, param_values=param_values)

    # ==============================================================
    # 2. PARAMETER SUMMARY
    # ==============================================================
    @app.route("/print/parameter-summary/<int:pid>")
    def print_parameter_summary(pid):
        p = one("SELECT * FROM parameters WHERE id=?", (pid,))
        if not p: abort(404)
        study_id = request.args.get("study_id", type=int)
        study = one("SELECT * FROM studies WHERE id=?", (study_id,)) if study_id else None
        rows = _values_for(pid, study_id)
        latest = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None:
                continue
            latest[r["participant_code"]] = {
                "value": r["numeric_value"],
                "group": r["group_type"] or "Unclassified",
            }
        values = [v["value"] for v in latest.values()]
        stats = descriptive(values) if values else {"n": 0}
        return render_template("print_parameter_summary.html",
                               p=p, latest=latest, stats=stats, study=study)

    # ==============================================================
    # 3. GROUP COMPARISON
    # ==============================================================
    @app.route("/print/group-comparison/<int:sid>")
    def print_group_comparison(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        param_id = request.args.get("parameter_id", type=int)
        if not param_id:
            flash("Pick a parameter for group comparison.", "info")
            return redirect(url_for("print_hub"))
        p = one("SELECT * FROM parameters WHERE id=?", (param_id,))
        if not p: abort(404)
        rows = _values_for(param_id, sid)
        groups = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None:
                continue
            gname = r["group_type"] or "Unclassified"
            groups.setdefault(gname, []).append(r["numeric_value"])
        names = sorted(groups.keys())
        result = None
        if len(names) >= 2:
            result = compare_groups(groups[names[0]], groups[names[1]])
            result["g1"] = names[0]; result["g2"] = names[1]
        group_stats = {n: descriptive(v) for n, v in groups.items()}
        chart = _chart_png_b64("bar_group", groups, f"{p['name']} by group") if groups else None
        return render_template("print_group_comparison.html",
                               s=s, p=p, groups=groups, group_stats=group_stats,
                               result=result, chart=chart)

    # ==============================================================
    # 4. STUDY PROGRESS
    # ==============================================================
    @app.route("/print/study-progress/<int:sid>")
    def print_study_progress(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        parts = query("SELECT * FROM participants WHERE study_id=? AND archived=0", (sid,))
        consent   = {"Obtained": 0, "Pending": 0, "Declined": 0}
        screening = {"Screened": 0, "Eligible": 0, "Ineligible": 0}
        enroll    = {"Enrolled": 0, "Withdrawn": 0, "Completed": 0}
        groups = {}
        for p in parts:
            if p["consent_status"] in consent: consent[p["consent_status"]] += 1
            if p["screening_status"] in screening: screening[p["screening_status"]] += 1
            if p["enrollment_status"] in enroll: enroll[p["enrollment_status"]] += 1
            gg = p["group_type"] or "Unclassified"
            groups[gg] = groups.get(gg, 0) + 1
        n_records = one("""SELECT COUNT(*) n FROM participant_records r
                           JOIN participants p ON p.id=r.participant_id
                           WHERE p.study_id=?""", (sid,))["n"]
        return render_template("print_study_progress.html",
                               s=s, n=len(parts), consent=consent,
                               screening=screening, enrollment=enroll,
                               groups=groups, n_records=n_records)

    # ==============================================================
    # 5. QUALITY REPORT
    # ==============================================================
    @app.route("/print/quality-report")
    def print_quality_report():
        rows = query("""SELECT q.*, p.participant_code, pa.name AS parameter_name
                        FROM quality_checks q
                        LEFT JOIN participants p ON p.id=q.participant_id
                        LEFT JOIN parameters pa ON pa.id=q.parameter_id
                        WHERE q.resolved=0
                        ORDER BY q.severity, q.id DESC""")
        by_sev = {}
        for r in rows:
            by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
        return render_template("print_quality_report.html",
                               rows=rows, by_sev=by_sev)

    # ==============================================================
    # 6. BLANK DATA FORM
    # ==============================================================
    @app.route("/print/blank-form")
    def print_blank_form():
        study_id = request.args.get("study_id", type=int)
        study = one("SELECT * FROM studies WHERE id=?", (study_id,)) if study_id else None
        params = query("""SELECT * FROM parameters WHERE active=1
                          ORDER BY category, sort_order, name""")
        grouped = {}
        for p in params:
            cat = p["category"] or "Other"
            grouped.setdefault(cat, []).append(p)
        return render_template("print_blank_form.html",
                               study=study, grouped=grouped)

    # ==============================================================
    # 7. STATISTICS REPORT
    # ==============================================================
    @app.route("/print/statistics/<int:sid>")
    def print_statistics(sid):
        s = one("SELECT * FROM studies WHERE id=?", (sid,))
        if not s: abort(404)
        param_id = request.args.get("parameter_id", type=int)
        if not param_id:
            flash("Pick a parameter for the statistics report.", "info")
            return redirect(url_for("print_hub"))
        p = one("SELECT * FROM parameters WHERE id=?", (param_id,))
        if not p: abort(404)
        rows = _values_for(param_id, sid)
        values = [r["numeric_value"] for r in rows
                  if r["value_state"] == "VALUE" and r["numeric_value"] is not None]
        desc = descriptive(values) if values else {"n": 0}
        norm = normality_test(values) if len(values) >= 3 else {"available": False}
        groups = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None:
                continue
            gname = r["group_type"] or "Unclassified"
            groups.setdefault(gname, []).append(r["numeric_value"])
        names = sorted(groups.keys())
        comparison = None
        if len(names) >= 2:
            comparison = compare_groups(groups[names[0]], groups[names[1]])
            comparison["g1"] = names[0]; comparison["g2"] = names[1]
        chart = _chart_png_b64("hist", values, p["name"]) if values else None
        return render_template("print_statistics.html",
                               s=s, p=p, desc=desc, norm=norm,
                               groups=groups, comparison=comparison,
                               chart=chart)
