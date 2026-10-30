"""Inter-rater reliability — kappa, weighted kappa, ICC, Bland-Altman."""
from flask import render_template, request, jsonify
from database import query
from reliability import (cohens_kappa, weighted_kappa,
                         icc_2_1, icc_3_1, bland_altman)


def register(app):

    @app.route("/reliability")
    def reliability_page():
        params = query("""SELECT id, code, name, unit, category, data_type
                          FROM parameters WHERE active=1
                          ORDER BY category, sort_order, name""")
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("reliability.html", params=params, studies=studies)

    @app.post("/reliability/compute")
    def reliability_compute():
        pid = request.form.get("parameter_id")
        sid = request.form.get("study_id") or None
        if not pid:
            return jsonify(error="Select a parameter"), 400
        sql = """SELECT p.participant_code, p.id AS pid,
                        v.numeric_value, v.value_text, v.value_state,
                        pa.data_type
                 FROM participant_values v
                 JOIN participant_records r ON r.id=v.record_id
                 JOIN participants p ON p.id=r.participant_id
                 JOIN parameters pa ON pa.id=v.parameter_id
                 WHERE v.parameter_id=? AND p.archived=0"""
        args = [pid]
        if sid:
            sql += " AND p.study_id=?"; args.append(sid)
        sql += " ORDER BY p.id, r.id, v.id"
        rows = query(sql, args)

        by_part = {}
        for r in rows:
            if r["value_state"] != "VALUE": continue
            raw = r["numeric_value"] if r["numeric_value"] is not None else r["value_text"]
            by_part.setdefault(r["participant_code"], []).append(raw)

        pairs = [(v[0], v[1]) for v in by_part.values() if len(v) >= 2]
        if len(pairs) < 3:
            return jsonify(error=(
                f"Only {len(pairs)} participants have ≥ 2 entries for this parameter. "
                "Enter the same measurement twice (two raters / re-entry) for at least 3 subjects."))
        dtype = rows[0]["data_type"] if rows else "Decimal"
        firsts  = [p[0] for p in pairs]
        seconds = [p[1] for p in pairs]
        out = {"n_pairs": len(pairs), "data_type": dtype,
               "sample": [{"rater1": p[0], "rater2": p[1]} for p in pairs[:10]]}
        if dtype in ("Integer","Decimal"):
            out["icc_2_1"] = icc_2_1(list(zip(firsts, seconds)))
            out["icc_3_1"] = icc_3_1(list(zip(firsts, seconds)))
            try:
                out["bland_altman"] = bland_altman([float(x) for x in firsts],
                                                    [float(x) for x in seconds])
            except (TypeError, ValueError):
                out["bland_altman"] = {"error": "Non-numeric values present"}
            try:
                out["weighted_kappa"] = weighted_kappa(firsts, seconds, "linear")
            except Exception:
                out["weighted_kappa"] = {"error": "Cannot compute"}
        else:
            out["kappa"] = cohens_kappa(firsts, seconds)
        return jsonify(out)
