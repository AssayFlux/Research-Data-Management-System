"""Recruitment funnel — Screened → Eligible → Consented → Enrolled → Completed."""
from flask import render_template, request, abort
from database import query, one


def register(app):

    @app.route("/recruitment")
    def recruitment_page():
        studies = query("SELECT id,study_code,title,sample_target FROM studies WHERE archived=0 ORDER BY title")
        sid = request.args.get("study_id", type=int)
        if not sid and studies:
            sid = studies[0]["id"]
        data = None
        if sid:
            s = one("SELECT * FROM studies WHERE id=?", (sid,))
            if not s: abort(404)
            parts = query("SELECT * FROM participants WHERE study_id=? AND archived=0", (sid,))
            counts = {
                "screened":     len(parts),
                "eligible":     sum(1 for p in parts if (p["screening_status"] or "") == "Eligible"),
                "ineligible":   sum(1 for p in parts if (p["screening_status"] or "") == "Ineligible"),
                "consented":    sum(1 for p in parts if (p["consent_status"] or "") == "Obtained"),
                "enrolled":     sum(1 for p in parts if (p["enrollment_status"] or "") == "Enrolled"),
                "completed":    sum(1 for p in parts if (p["enrollment_status"] or "") == "Completed"),
                "withdrawn":    sum(1 for p in parts if (p["enrollment_status"] or "") == "Withdrawn"),
                "control":      sum(1 for p in parts if (p["classification"] or "") == "Control"),
                "study":        sum(1 for p in parts if (p["classification"] or "") == "Study"),
                "excluded":     sum(1 for p in parts if (p["classification"] or "") == "Excluded"),
                "undetermined": sum(1 for p in parts if (p["classification"] or "Undetermined") == "Undetermined"),
            }
            target = s["sample_target"] or 0
            pct = (counts["enrolled"] / target * 100) if target else 0
            monthly = query("""SELECT substr(created_at,1,7) AS ym, COUNT(*) AS n
                               FROM participants WHERE study_id=? AND archived=0
                               GROUP BY ym ORDER BY ym""", (sid,))
            data = {"study": s, "counts": counts, "target": target,
                    "pct": round(pct, 1), "monthly": monthly}
        return render_template("recruitment.html", studies=studies, data=data, selected=sid)
