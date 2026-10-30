"""Per-participant longitudinal trends."""
from flask import render_template, request, jsonify
from database import query
from statistics import descriptive, linear_regression


def register(app):

    @app.route("/longitudinal")
    def longitudinal_page():
        params = query("""SELECT id, code, name, unit, category FROM parameters
                          WHERE active=1 ORDER BY category, sort_order, name""")
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("longitudinal.html", params=params, studies=studies)

    @app.post("/longitudinal/data")
    def longitudinal_data():
        pid = request.form.get("parameter_id")
        sid = request.form.get("study_id") or None
        part_filter = request.form.get("participant_id") or None
        if not pid:
            return jsonify(error="Select a parameter"), 400
        sql = """SELECT r.id AS record_id, r.visit_date, r.created_at,
                        v.numeric_value, v.value_state,
                        p.id AS participant_id, p.participant_code,
                        p.classification, p.group_type, s.study_code
                 FROM participant_values v
                 JOIN participant_records r ON r.id=v.record_id
                 JOIN participants p ON p.id=r.participant_id
                 JOIN studies s ON s.id=p.study_id
                 WHERE v.parameter_id=? AND p.archived=0"""
        args = [pid]
        if sid:
            sql += " AND p.study_id=?"; args.append(sid)
        if part_filter:
            sql += " AND p.id=?"; args.append(part_filter)
        sql += " ORDER BY p.id, COALESCE(r.visit_date, r.created_at), r.id"
        rows = query(sql, args)

        series = {}
        for r in rows:
            if r["value_state"] != "VALUE" or r["numeric_value"] is None: continue
            code = r["participant_code"]
            series.setdefault(code, {
                "participant_code": code,
                "classification": r["classification"] or "Undetermined",
                "group_type": r["group_type"] or "",
                "points": [],
            })["points"].append({
                "x": r["visit_date"] or r["created_at"],
                "y": r["numeric_value"],
                "record_id": r["record_id"],
            })

        for code, s in series.items():
            ys = [p["y"] for p in s["points"]]
            s["descriptive"] = descriptive(ys)
            if len(ys) >= 3:
                s["trend"] = linear_regression(list(range(len(ys))), ys)
            else:
                s["trend"] = None

        max_visits = max((len(s["points"]) for s in series.values()), default=0)
        cohort_mean = []
        for i in range(max_visits):
            vals = [s["points"][i]["y"] for s in series.values() if i < len(s["points"])]
            if vals:
                cohort_mean.append({"visit": i + 1,
                                    "mean": round(sum(vals)/len(vals), 4),
                                    "n": len(vals)})

        return jsonify(series=series, cohort_mean=cohort_mean,
                       n_participants=len(series),
                       n_records=sum(len(s["points"]) for s in series.values()))
