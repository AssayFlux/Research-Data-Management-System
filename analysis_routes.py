"""International-grade analysis routes with classification + records-mode filters."""
from functools import wraps
from flask import (render_template, request, redirect, url_for,
                   flash, abort, g, jsonify)
from database import query, one, execute
from statistics import (descriptive, outlier_detect, normality_test, levene_test,
                        ttest_independent, ttest_paired, mannwhitney, wilcoxon,
                        compare_auto, anova_oneway, kruskal_wallis, tukey_hsd,
                        chi_square, fisher_exact, correlation,
                        linear_regression, predict_linear,
                        roc_analysis, diagnostic_accuracy,
                        trend_forecast, moving_average, exponential_smoothing,
                        sample_size_mean, sample_size_proportion)
from analysis_filters import (fetch_values, fetch_single, fetch_paired,
                              groups_by_classification,
                              formulas_for_parameter, formula_input_codes,
                              VALID_MODES, VALID_CLASSES)


def _chart_png_b64(kind, data, title="", xlabel="", ylabel=""):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        fig, ax = plt.subplots(figsize=(6.5, 3.4), dpi=110)
        if kind == "hist":
            arr = np.array(data)
            ax.hist(arr, bins=min(20, max(5, len(arr) // 2)),
                    color="#059669", edgecolor="white")
        elif kind == "box":
            ax.boxplot(np.array(data), vert=True, patch_artist=True,
                       boxprops=dict(facecolor="#a7f3d0", color="#059669"),
                       medianprops=dict(color="#065f46", linewidth=2))
        elif kind == "bar":
            names, vals = data
            bars = ax.bar(names, vals, color="#059669")
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width()/2, v, f"{v:.2f}",
                        ha="center", va="bottom", fontsize=9)
        elif kind == "scatter":
            xs, ys, line = data
            ax.scatter(xs, ys, color="#059669", s=26, alpha=0.7)
            if line:
                x_l, y_l = line
                ax.plot(x_l, y_l, color="#dc2626", linewidth=2)
        elif kind == "line":
            xs, ys = data
            ax.plot(xs, ys, color="#059669", marker="o", markersize=4)
        elif kind == "roc":
            fpr, tpr, auc_val = data
            ax.plot(fpr, tpr, color="#059669", linewidth=2, label=f"AUC={auc_val:.3f}")
            ax.plot([0,1], [0,1], "--", color="#94a3b8", linewidth=1)
            ax.set_xlabel("1 – Specificity"); ax.set_ylabel("Sensitivity")
            ax.legend(loc="lower right")
        elif kind == "error_bars":
            names, means, sds = data
            ax.bar(names, means, yerr=sds, capsize=5, color="#059669", edgecolor="white")
        else:
            plt.close(fig); return None
        if title: ax.set_title(title, fontsize=10)
        if xlabel: ax.set_xlabel(xlabel, fontsize=9)
        if ylabel: ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(True, alpha=0.3, linestyle=":")
        ax.tick_params(labelsize=8)
        fig.tight_layout()
        import io, base64
        buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


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

    # ── read filters from request ──
    def get_filters():
        sid = request.form.get("study_id") or request.args.get("study_id") or None
        cls = request.form.get("classification") or request.args.get("classification") or None
        mode = request.form.get("records_mode") or request.args.get("records_mode") or "latest"
        if cls not in VALID_CLASSES: cls = None
        if mode not in VALID_MODES:  mode = "latest"
        return sid, cls, mode

    # ═════════════════════════════════════════════════════
    # ANALYSIS HUB
    # ═════════════════════════════════════════════════════
    @app.route("/analysis")
    def analysis_hub():
        params = query("""SELECT id,code,name,unit,category FROM parameters
                          WHERE active=1 ORDER BY category, sort_order, name""")
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("analysis.html", params=params, studies=studies)

    # ── classify study for caption ──
    @app.post("/analysis/parameter-info")
    def analysis_parameter_info():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="No parameter"), 400
        p = one("SELECT * FROM parameters WHERE id=?", (pid,))
        if not p: return jsonify(error="Not found"), 404
        fmls = formulas_for_parameter(pid)
        return jsonify(name=p["name"], code=p["code"], unit=p["unit"],
                       ref_low=p["ref_low"], ref_high=p["ref_high"],
                       ref_text=p["ref_text"],
                       formulas=[{"name": f["name"], "code": f["code"],
                                  "expression": f["expression"],
                                  "inputs": formula_input_codes(f["id"])}
                                 for f in fmls])

    # ── DESCRIPTIVE ──
    @app.post("/analysis/descriptive")
    def analysis_descriptive():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        rows = fetch_values([int(pid)], sid, cls, mode)
        values = [r["numeric_value"] for r in rows
                  if r["value_state"] == "VALUE" and r["numeric_value"] is not None]
        missing = sum(1 for r in rows if r["value_state"] != "VALUE")
        out = descriptive(values)
        out["missing"] = missing
        out["total_rows"] = len(rows)
        out["mode"] = mode
        out["classification"] = cls or "All"
        out["outliers_iqr"] = outlier_detect(values, "iqr")
        out["outliers_z"]   = outlier_detect(values, "zscore")
        return jsonify(out)

    @app.post("/analysis/normality")
    def analysis_normality():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        values = fetch_single(int(pid), sid, cls, mode)
        groups = groups_by_classification(int(pid), sid, mode)
        out = {"overall": normality_test(values), "n": len(values)}
        if len(groups) >= 2:
            names = sorted(groups.keys())
            out["by_group"] = {n: normality_test(groups[n]) for n in names}
            out["levene"] = levene_test(groups[names[0]], groups[names[1]])
        return jsonify(out)

    @app.post("/analysis/compare")
    def analysis_compare():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        groups = groups_by_classification(int(pid), sid, mode)
        if len(groups) < 2:
            return jsonify(error="Need ≥ 2 groups. Ensure participants have different classifications (Study / Control) or group types.")
        names = sorted(groups.keys())
        a, b = groups[names[0]], groups[names[1]]
        result = compare_auto(a, b)
        result["group_a"] = names[0]; result["group_b"] = names[1]
        result["n_a"] = len(a); result["n_b"] = len(b)
        result["mean_a"] = round(sum(a)/len(a), 4) if a else 0
        result["mean_b"] = round(sum(b)/len(b), 4) if b else 0
        result["sd_a"] = descriptive(a).get("sd"); result["sd_b"] = descriptive(b).get("sd")
        result["median_a"] = descriptive(a).get("median")
        result["median_b"] = descriptive(b).get("median")
        result["normality_a"] = normality_test(a)
        result["normality_b"] = normality_test(b)
        return jsonify(result)

    @app.post("/analysis/multigroup")
    def analysis_multigroup():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        groups = groups_by_classification(int(pid), sid, mode)
        if len(groups) < 2:
            return jsonify(error="Need ≥ 2 groups")
        names = sorted(groups.keys())
        if len(names) == 2:
            return jsonify({"note": "Only 2 groups — using two-group comparison",
                            "result": compare_auto(groups[names[0]], groups[names[1]])})
        arrs = [groups[n] for n in names]
        all_normal = all(normality_test(g).get("shapiro_p", 0) >= 0.05 for g in arrs)
        if all_normal:
            return jsonify({"test": "parametric",
                            "anova": anova_oneway(*arrs),
                            "posthoc": tukey_hsd(arrs, names),
                            "groups": names,
                            "group_stats": [descriptive(g) for g in arrs]})
        return jsonify({"test": "non-parametric",
                        "kruskal": kruskal_wallis(*arrs),
                        "groups": names,
                        "group_stats": [descriptive(g) for g in arrs]})

    @app.post("/analysis/correlate")
    def analysis_correlate():
        xid = request.form.get("x_id"); yid = request.form.get("y_id")
        if not xid or not yid: return jsonify(error="Pick two parameters"), 400
        sid, cls, mode = get_filters()
        xs, ys = fetch_paired(int(xid), int(yid), sid, cls, mode)
        out = {"n_pairs": len(xs)}
        for method in ("pearson", "spearman", "kendall"):
            out[method] = correlation(xs, ys, method)
        out["linear_regression"] = linear_regression(xs, ys)
        return jsonify(out)

    @app.post("/analysis/regression")
    def analysis_regression():
        xid = request.form.get("x_id"); yid = request.form.get("y_id")
        if not xid or not yid: return jsonify(error="Pick two parameters"), 400
        sid, cls, mode = get_filters()
        xs, ys = fetch_paired(int(xid), int(yid), sid, cls, mode)
        if len(xs) < 3: return jsonify(error="Need ≥ 3 paired values")
        out = {"linear": linear_regression(xs, ys), "n": len(xs)}
        x_new = request.form.get("predict_x")
        if x_new:
            try: out["prediction"] = predict_linear(xs, ys, float(x_new))
            except ValueError: out["prediction"] = {"error": "Invalid x"}
        out["points"] = [{"x": xs[i], "y": ys[i]} for i in range(len(xs))]
        return jsonify(out)

    @app.post("/analysis/diagnostics")
    def analysis_diagnostics():
        yid = request.form.get("y_id")
        if not yid: return jsonify(error="Select the marker parameter"), 400
        sid, cls, mode = get_filters()
        rows = fetch_values([int(yid)], sid, cls, mode)
        cases = [r["numeric_value"] for r in rows
                 if r["value_state"] == "VALUE" and r["numeric_value"] is not None
                 and (r["classification"] or "").lower() == "study"]
        controls = [r["numeric_value"] for r in rows
                    if r["value_state"] == "VALUE" and r["numeric_value"] is not None
                    and (r["classification"] or "").lower() == "control"]
        if len(cases) < 2 or len(controls) < 2:
            return jsonify(error="Need ≥2 participants classified as 'Study' AND ≥2 as 'Control'. "
                                  "Use criteria to classify them.")
        y_true = [1]*len(cases) + [0]*len(controls)
        y_score = cases + controls
        roc = roc_analysis(y_true, y_score)
        best = {"youden_j": -1}
        for v in sorted(set(y_score)):
            r = diagnostic_accuracy(y_true, y_score, v)
            if r.get("youden_j", -1) > best.get("youden_j", -1):
                best = r
        return jsonify({"roc": roc, "n_cases": len(cases), "n_controls": len(controls),
                        "optimal_cutoff": best,
                        "stats_cases": descriptive(cases),
                        "stats_controls": descriptive(controls)})

    @app.post("/analysis/forecast")
    def analysis_forecast():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        values = fetch_single(int(pid), sid, cls, mode)
        steps = int(request.form.get("steps") or 3)
        return jsonify({"n": len(values),
                        "trend": trend_forecast(values, steps),
                        "moving_average": moving_average(values, 3),
                        "exp_smoothing": exponential_smoothing(values, 0.3),
                        "raw": values})

    @app.post("/analysis/sample-size")
    def analysis_sample_size():
        kind = request.form.get("kind", "mean")
        try:
            if kind == "mean":
                return jsonify(sample_size_mean(
                    float(request.form.get("sd", 1)),
                    float(request.form.get("margin", 1))))
            return jsonify(sample_size_proportion(
                float(request.form.get("p", 0.5)),
                float(request.form.get("margin", 0.05))))
        except ValueError:
            return jsonify(error="Numeric inputs required"), 400

    # ═════════════════════════════════════════════════════
    # GRAPHS
    # ═════════════════════════════════════════════════════
    # NOTE: /graphs route is defined in step5_routes.py — duplicate removed
    
    @app.post("/graphs/data")
    def graphs_data():
        pid = request.form.get("parameter_id")
        if not pid: return jsonify(error="Select a parameter"), 400
        sid, cls, mode = get_filters()
        rows = fetch_values([int(pid)], sid, cls, mode)
        values = [r["numeric_value"] for r in rows
                  if r["value_state"] == "VALUE" and r["numeric_value"] is not None]
        groups = groups_by_classification(int(pid), sid, mode)
        return jsonify(values=values, groups=groups, n=len(values),
                       stats=descriptive(values),
                       classification=cls or "All", mode=mode)

    @app.post("/graphs/pair")
    def graphs_pair():
        xid = request.form.get("x_id"); yid = request.form.get("y_id")
        if not xid or not yid: return jsonify(error="Pick two parameters"), 400
        sid, cls, mode = get_filters()
        xs, ys = fetch_paired(int(xid), int(yid), sid, cls, mode)
        return jsonify(xs=xs, ys=ys, n=len(xs),
                       regression=linear_regression(xs, ys))

    # ═════════════════════════════════════════════════════
    # PRINT — analysis report
    # ═════════════════════════════════════════════════════
    @app.route("/print/analysis")
    def print_analysis():
        sid = request.args.get("study_id", type=int) or None
        pid = request.args.get("parameter_id", type=int)
        cls = request.args.get("classification") or None
        mode = request.args.get("records_mode") or "latest"
        if mode not in VALID_MODES: mode = "latest"
        if not pid:
            flash("Pick a parameter to print the analysis.", "info")
            return redirect(url_for("print_hub"))
        p = one("SELECT * FROM parameters WHERE id=?", (pid,))
        if not p: abort(404)
        s = one("SELECT * FROM studies WHERE id=?", (sid,)) if sid else None
        values = fetch_single(pid, sid, cls, mode)
        desc = descriptive(values)
        norm = normality_test(values)
        groups = groups_by_classification(pid, sid, mode)
        comparison = None
        if len(groups) >= 2:
            names = sorted(groups.keys())
            comparison = compare_auto(groups[names[0]], groups[names[1]])
            comparison["group_a"] = names[0]; comparison["group_b"] = names[1]
        chart_hist = _chart_png_b64("hist", values, p["name"]) if values else None
        chart_box  = _chart_png_b64("box", values, f"{p['name']} distribution") if values else None
        chart_groups = None
        if groups:
            names = sorted(groups.keys())
            means = [sum(groups[n]) / len(groups[n]) if groups[n] else 0 for n in names]
            sds   = [descriptive(groups[n]).get("sd", 0) for n in names]
            chart_groups = _chart_png_b64("error_bars", (names, means, sds),
                                          f"{p['name']} by group")
        # Computed-parameter footnote
        fmls = formulas_for_parameter(pid)
        computed_notes = [{"name": f["name"], "code": f["code"],
                           "expression": f["expression"],
                           "inputs": formula_input_codes(f["id"])} for f in fmls]
        return render_template("print_analysis.html",
                               s=s, p=p, desc=desc, norm=norm,
                               comparison=comparison, groups=groups,
                               chart_hist=chart_hist, chart_box=chart_box,
                               chart_groups=chart_groups, n=len(values),
                               computed_notes=computed_notes,
                               filters={"classification": cls or "All", "mode": mode})
