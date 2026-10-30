"""Professional statistics engine — everything from t-tests to prediction."""
import math

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def _clean(values):
    out = []
    for v in values:
        try:
            if v is None or v == "": continue
            out.append(float(v))
        except (TypeError, ValueError): pass
    return out

def _mean(x): return sum(x) / len(x) if x else 0

def _median(x):
    if not x: return 0
    s = sorted(x); n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

def _stdev(x):
    if len(x) < 2: return 0
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))

def _quantile(x, q):
    if not x: return 0
    s = sorted(x); n = len(s)
    pos = q * (n - 1)
    lo = int(pos); hi = min(lo + 1, n - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)

def _skewness(x):
    n = len(x)
    if n < 3: return 0
    m = _mean(x); sd = _stdev(x)
    if sd == 0: return 0
    return (n / ((n - 1) * (n - 2))) * sum(((v - m) / sd) ** 3 for v in x)

def _kurtosis(x):
    n = len(x)
    if n < 4: return 0
    m = _mean(x); sd = _stdev(x)
    if sd == 0: return 0
    m4 = sum((v - m) ** 4 for v in x) / n
    return (m4 / sd ** 4) - 3

def _scipy():
    try:
        import scipy.stats as s
        return s
    except Exception:
        return None

def _r(v, n=4):
    try: return round(float(v), n)
    except (TypeError, ValueError): return v

# ═══════════════════════════════════════════════════════════
# DESCRIPTIVE
# ═══════════════════════════════════════════════════════════
def descriptive(values):
    x = _clean(values)
    if not x: return {"n": 0}
    n = len(x); mean = _mean(x); sd = _stdev(x)
    se = sd / math.sqrt(n) if n else 0
    ci = 1.96 * se
    return {
        "n": n,
        "mean": _r(mean), "sd": _r(sd), "se": _r(se),
        "median": _r(_median(x)),
        "q1": _r(_quantile(x, .25)), "q3": _r(_quantile(x, .75)),
        "iqr": _r(_quantile(x, .75) - _quantile(x, .25)),
        "min": _r(min(x)), "max": _r(max(x)),
        "range": _r(max(x) - min(x)),
        "ci95_low": _r(mean - ci), "ci95_high": _r(mean + ci),
        "cv": _r(sd / mean * 100) if mean else None,
        "skewness": _r(_skewness(x)), "kurtosis": _r(_kurtosis(x)),
    }

def outlier_detect(values, method="iqr"):
    """method: iqr | zscore | modified_z"""
    x = _clean(values)
    out = {"method": method, "outliers": [], "lower_fence": None, "upper_fence": None}
    if len(x) < 4: return out
    if method == "iqr":
        q1 = _quantile(x, .25); q3 = _quantile(x, .75); iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        out["lower_fence"] = _r(lo); out["upper_fence"] = _r(hi)
        out["outliers"] = [v for v in x if v < lo or v > hi]
    elif method == "zscore":
        m = _mean(x); sd = _stdev(x)
        if sd == 0: return out
        out["lower_fence"] = _r(m - 3 * sd); out["upper_fence"] = _r(m + 3 * sd)
        out["outliers"] = [v for v in x if abs((v - m) / sd) > 3]
    elif method == "modified_z":
        med = _median(x); mad = _median([abs(v - med) for v in x])
        if mad == 0: return out
        out["outliers"] = [v for v in x if abs(0.6745 * (v - med) / mad) > 3.5]
    out["n_outliers"] = len(out["outliers"])
    return out

# ═══════════════════════════════════════════════════════════
# NORMALITY & VARIANCE
# ═══════════════════════════════════════════════════════════
def normality_test(values):
    x = _clean(values); s = _scipy()
    if not s or len(x) < 3: return {"available": False}
    out = {"available": True, "n": len(x)}
    try:
        r = s.shapiro(x)
        out["shapiro_statistic"] = _r(r.statistic)
        out["shapiro_p"] = _r(r.pvalue)
        out["shapiro_verdict"] = "Normal" if r.pvalue >= 0.05 else "Non-normal"
    except Exception: pass
    if len(x) >= 8:
        try:
            r = s.normaltest(x)
            out["dagostino_statistic"] = _r(r.statistic)
            out["dagostino_p"] = _r(r.pvalue)
            out["dagostino_verdict"] = "Normal" if r.pvalue >= 0.05 else "Non-normal"
        except Exception: pass
    out["verdict"] = out.get("shapiro_verdict", "Unknown")
    return out

def levene_test(a, b):
    s = _scipy(); a, b = _clean(a), _clean(b)
    if not s or len(a) < 2 or len(b) < 2: return {"available": False}
    try:
        r = s.levene(a, b, center="median")
        return {"available": True, "statistic": _r(r.statistic),
                "p": _r(r.pvalue),
                "verdict": "Equal variances" if r.pvalue >= 0.05 else "Unequal variances"}
    except Exception:
        return {"available": False}

# ═══════════════════════════════════════════════════════════
# EFFECT SIZES
# ═══════════════════════════════════════════════════════════
def _cohens_d(a, b):
    na, nb = len(a), len(b)
    if na < 2 or nb < 2: return None
    sa, sb = _stdev(a), _stdev(b)
    pooled = math.sqrt(((na - 1) * sa ** 2 + (nb - 1) * sb ** 2) / (na + nb - 2))
    if pooled == 0: return 0
    return (_mean(a) - _mean(b)) / pooled

def _interpret_d(d):
    if d is None: return None
    a = abs(d)
    if a < 0.2: return "negligible"
    if a < 0.5: return "small"
    if a < 0.8: return "medium"
    return "large"

# ═══════════════════════════════════════════════════════════
# COMPARISON TESTS
# ═══════════════════════════════════════════════════════════
def ttest_independent(a, b, welch=True):
    s = _scipy(); a, b = _clean(a), _clean(b)
    if not s: return {"error": "scipy not installed"}
    if len(a) < 2 or len(b) < 2: return {"error": "Need ≥ 2 values per group"}
    r = s.ttest_ind(a, b, equal_var=not welch)
    d = _cohens_d(a, b)
    return {
        "test": "Welch t-test" if welch else "Student t-test",
        "statistic": _r(r.statistic), "p": _r(r.pvalue),
        "mean_a": _r(_mean(a)), "mean_b": _r(_mean(b)),
        "mean_diff": _r(_mean(a) - _mean(b)),
        "cohens_d": _r(d), "effect_size": _interpret_d(d),
        "n_a": len(a), "n_b": len(b),
    }

def ttest_paired(a, b):
    s = _scipy()
    n = min(len(a), len(b))
    if n < 2: return {"error": "Need ≥ 2 pairs"}
    a, b = _clean(a)[:n], _clean(b)[:n]
    r = s.ttest_rel(a, b)
    d = _cohens_d(a, b)
    return {"test": "Paired t-test", "statistic": _r(r.statistic), "p": _r(r.pvalue),
            "mean_diff": _r(_mean(a) - _mean(b)), "n": n,
            "cohens_d": _r(d), "effect_size": _interpret_d(d)}

def mannwhitney(a, b):
    s = _scipy(); a, b = _clean(a), _clean(b)
    if not s: return {"error": "scipy not installed"}
    if len(a) < 1 or len(b) < 1: return {"error": "Need values in both groups"}
    r = s.mannwhitneyu(a, b, alternative="two-sided")
    na, nb = len(a), len(b)
    u = float(r.statistic)
    rbc = 1 - (2 * u) / (na * nb)
    return {"test": "Mann-Whitney U", "statistic": _r(u), "p": _r(r.pvalue),
            "n_a": na, "n_b": nb, "rank_biserial": _r(rbc),
            "median_a": _r(_median(a)), "median_b": _r(_median(b))}

def wilcoxon(a, b):
    s = _scipy()
    n = min(len(a), len(b))
    if n < 5: return {"error": "Need ≥ 5 pairs"}
    a, b = _clean(a)[:n], _clean(b)[:n]
    r = s.wilcoxon(a, b)
    return {"test": "Wilcoxon signed-rank", "statistic": _r(r.statistic),
            "p": _r(r.pvalue), "n": n}

def compare_auto(a, b, paired=False):
    """Auto-select parametric vs non-parametric based on normality."""
    a, b = _clean(a), _clean(b)
    if paired:
        return ttest_paired(a, b)
    na, nb = normality_test(a), normality_test(b)
    both_normal = (na.get("shapiro_p", 0) >= 0.05 and
                   nb.get("shapiro_p", 0) >= 0.05) if na.get("available") and nb.get("available") else False
    if both_normal and len(a) >= 3 and len(b) >= 3:
        out = ttest_independent(a, b, welch=True)
        out["selection_reason"] = "Both groups normal (Shapiro p ≥ 0.05) → parametric test"
        return out
    out = mannwhitney(a, b)
    out["selection_reason"] = "Non-normal distribution → non-parametric test"
    return out

# ═══════════════════════════════════════════════════════════
# MULTI-GROUP
# ═══════════════════════════════════════════════════════════
def anova_oneway(*groups):
    s = _scipy()
    if not s: return {"error": "scipy not installed"}
    g = [_clean(x) for x in groups if _clean(x)]
    if len(g) < 2: return {"error": "Need ≥ 2 groups"}
    r = s.f_oneway(*g)
    # eta²
    gm = _mean([v for grp in g for v in grp])
    ss_between = sum(len(grp) * (_mean(grp) - gm) ** 2 for grp in g)
    ss_total = sum((v - gm) ** 2 for grp in g for v in grp)
    eta2 = ss_between / ss_total if ss_total else 0
    return {"test": "One-way ANOVA", "statistic": _r(r.statistic),
            "p": _r(r.pvalue), "eta_squared": _r(eta2),
            "n_groups": len(g), "n_total": sum(len(grp) for grp in g),
            "group_means": [_r(_mean(grp)) for grp in g]}

def kruskal_wallis(*groups):
    s = _scipy()
    if not s: return {"error": "scipy not installed"}
    g = [_clean(x) for x in groups if _clean(x)]
    if len(g) < 2: return {"error": "Need ≥ 2 groups"}
    r = s.kruskal(*g)
    n_total = sum(len(grp) for grp in g)
    eps2 = r.statistic / (n_total - 1) if n_total > 1 else 0
    return {"test": "Kruskal-Wallis", "statistic": _r(r.statistic),
            "p": _r(r.pvalue), "epsilon_squared": _r(eps2),
            "n_groups": len(g), "n_total": n_total}

def tukey_hsd(groups, labels=None):
    s = _scipy()
    if not s: return {"error": "scipy not installed"}
    clean = [_clean(g) for g in groups]
    if len(clean) < 2: return {"error": "Need ≥ 2 groups"}
    try:
        r = s.tukey_hsd(*clean)
        pairs = []
        k = len(clean)
        for i in range(k):
            for j in range(i + 1, k):
                pairs.append({
                    "group_a": (labels[i] if labels else f"G{i+1}"),
                    "group_b": (labels[j] if labels else f"G{j+1}"),
                    "statistic": _r(r.statistic[i][j]),
                    "p": _r(r.pvalue[i][j]),
                })
        return {"test": "Tukey HSD", "pairs": pairs}
    except Exception as e:
        return {"error": f"Tukey HSD unavailable: {e}"}

# ═══════════════════════════════════════════════════════════
# CATEGORICAL
# ═══════════════════════════════════════════════════════════
def chi_square(table):
    s = _scipy()
    if not s: return {"error": "scipy not installed"}
    try:
        chi2, p, dof, _ = s.chi2_contingency(table)
        n = sum(sum(row) for row in table)
        min_dim = min(len(table), len(table[0])) - 1
        cramers_v = math.sqrt(chi2 / (n * min_dim)) if n * min_dim else 0
        return {"test": "Chi-square", "chi2": _r(chi2), "p": _r(p),
                "dof": int(dof), "cramers_v": _r(cramers_v), "n": n}
    except Exception as e:
        return {"error": str(e)}

def fisher_exact(table):
    s = _scipy()
    if not s: return {"error": "scipy not installed"}
    try:
        odds, p = s.fisher_exact(table)
        return {"test": "Fisher's exact", "odds_ratio": _r(odds), "p": _r(p)}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════
# CORRELATION
# ═══════════════════════════════════════════════════════════
def correlation(a, b, method="pearson"):
    s = _scipy()
    a, b = _clean(a), _clean(b)
    n = min(len(a), len(b))
    if n < 3: return {"error": "Need ≥ 3 pairs"}
    a, b = a[:n], b[:n]
    if not s: return {"error": "scipy not installed"}
    try:
        if method == "pearson":
            r, p = s.pearsonr(a, b)
            # Fisher z CI
            z = math.atanh(r)
            se = 1 / math.sqrt(n - 3)
            lo, hi = math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)
            return {"method": "Pearson", "coefficient": _r(r), "p": _r(p),
                    "n": n, "r_squared": _r(r ** 2),
                    "ci95_low": _r(lo), "ci95_high": _r(hi)}
        elif method == "spearman":
            r, p = s.spearmanr(a, b)
            return {"method": "Spearman", "coefficient": _r(r), "p": _r(p), "n": n}
        elif method == "kendall":
            r, p = s.kendalltau(a, b)
            return {"method": "Kendall", "coefficient": _r(r), "p": _r(p), "n": n}
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Unknown method"}

# ═══════════════════════════════════════════════════════════
# REGRESSION + PREDICTION
# ═══════════════════════════════════════════════════════════
def linear_regression(x, y):
    s = _scipy()
    x, y = _clean(x), _clean(y)
    n = min(len(x), len(y))
    if n < 3: return {"error": "Need ≥ 3 pairs"}
    x, y = x[:n], y[:n]
    if not s: return {"error": "scipy not installed"}
    try:
        r = s.linregress(x, y)
        residuals = [y[i] - (r.intercept + r.slope * x[i]) for i in range(n)]
        sse = sum(e ** 2 for e in residuals)
        sst = sum((yi - _mean(y)) ** 2 for yi in y)
        r2 = 1 - (sse / sst) if sst else 0
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - 2) if n > 2 else r2
        return {
            "test": "Linear regression",
            "slope": _r(r.slope), "intercept": _r(r.intercept),
            "r": _r(r.rvalue), "r_squared": _r(r2), "adj_r_squared": _r(adj_r2),
            "p": _r(r.pvalue), "stderr": _r(r.stderr),
            "n": n,
            "equation": f"y = {_r(r.slope, 3)}·x + {_r(r.intercept, 3)}",
        }
    except Exception as e:
        return {"error": str(e)}

def predict_linear(x, y, x_new):
    """Predict y for a new x, with 95% prediction interval."""
    s = _scipy()
    x, y = _clean(x), _clean(y)
    n = min(len(x), len(y))
    if n < 3: return {"error": "Need ≥ 3 pairs"}
    x, y = x[:n], y[:n]
    try:
        r = s.linregress(x, y)
        y_hat = r.intercept + r.slope * x_new
        # SE of prediction
        xm = _mean(x)
        sxx = sum((xi - xm) ** 2 for xi in x)
        resid = [y[i] - (r.intercept + r.slope * x[i]) for i in range(n)]
        s_res = math.sqrt(sum(e ** 2 for e in resid) / (n - 2)) if n > 2 else 0
        se_pred = s_res * math.sqrt(1 + 1 / n + (x_new - xm) ** 2 / sxx) if sxx else 0
        return {
            "x_new": x_new, "predicted_y": _r(y_hat),
            "pi95_low": _r(y_hat - 1.96 * se_pred),
            "pi95_high": _r(y_hat + 1.96 * se_pred),
            "slope": _r(r.slope), "intercept": _r(r.intercept),
            "n": n,
        }
    except Exception as e:
        return {"error": str(e)}

def multiple_regression(y, xs, names=None):
    """y: list; xs: dict name -> list."""
    try:
        import numpy as np
        yv = np.array(_clean(y))
        predictors = {k: _clean(v) for k, v in xs.items()}
        n = min(len(yv), *(len(v) for v in predictors.values())) if predictors else len(yv)
        if n < len(predictors) + 2:
            return {"error": f"Need ≥ {len(predictors)+2} rows"}
        cols = [np.array(predictors[k])[:n] for k in predictors]
        X = np.column_stack([np.ones(n)] + cols)
        yv = yv[:n]
        beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
        y_hat = X @ beta
        ss_res = float(((yv - y_hat) ** 2).sum())
        ss_tot = float(((yv - yv.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot else 0
        k = len(predictors)
        adj = 1 - (1 - r2) * (n - 1) / (n - k - 1) if n > k + 1 else r2
        return {
            "test": "Multiple linear regression",
            "n": n, "predictors": list(predictors.keys()),
            "intercept": _r(float(beta[0])),
            "coefficients": [_r(float(b)) for b in beta[1:]],
            "r_squared": _r(r2), "adj_r_squared": _r(adj),
        }
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════
# ROC / DIAGNOSTIC ACCURACY
# ═══════════════════════════════════════════════════════════
def roc_analysis(y_true, y_score):
    """y_true: 0/1 labels; y_score: numeric values."""
    try:
        from numpy import array
        yt = array([1 if float(v) == 1 else 0 for v in y_true])
        ys = array([float(v) for v in y_score])
        if len(set(yt.tolist())) < 2:
            return {"error": "Need both positive and negative cases"}
        # AUC by trapezoid rule using thresholds
        thresh = sorted(set(ys.tolist()))
        tprs, fprs = [0], [0]
        P = (yt == 1).sum(); N = (yt == 0).sum()
        for t in thresh:
            pred = (ys >= t).astype(int)
            tp = int(((pred == 1) & (yt == 1)).sum())
            fp = int(((pred == 1) & (yt == 0)).sum())
            tprs.append(tp / P if P else 0)
            fprs.append(fp / N if N else 0)
        tprs.append(1); fprs.append(1)
        auc = 0.0
        for i in range(1, len(fprs)):
            auc += (fprs[i] - fprs[i-1]) * (tprs[i] + tprs[i-1]) / 2
        return {"auc": _r(auc), "n_positive": int(P), "n_negative": int(N),
                "roc_points": [{"fpr": _r(fprs[i]), "tpr": _r(tprs[i])}
                               for i in range(len(fprs))]}
    except Exception as e:
        return {"error": str(e)}

def diagnostic_accuracy(y_true, y_score, cutoff):
    """Compute sensitivity, specificity, PPV, NPV, F1, Youden, accuracy."""
    try:
        yt = [1 if float(v) == 1 else 0 for v in y_true]
        ys = [float(v) for v in y_score]
        pred = [1 if v >= cutoff else 0 for v in ys]
        tp = sum(1 for a, b in zip(yt, pred) if a == 1 and b == 1)
        tn = sum(1 for a, b in zip(yt, pred) if a == 0 and b == 0)
        fp = sum(1 for a, b in zip(yt, pred) if a == 0 and b == 1)
        fn = sum(1 for a, b in zip(yt, pred) if a == 1 and b == 0)
        sens = tp / (tp + fn) if (tp + fn) else 0
        spec = tn / (tn + fp) if (tn + fp) else 0
        ppv = tp / (tp + fp) if (tp + fp) else 0
        npv = tn / (tn + fn) if (tn + fn) else 0
        acc = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0
        f1 = 2 * ppv * sens / (ppv + sens) if (ppv + sens) else 0
        youden = sens + spec - 1
        return {"cutoff": cutoff, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                "sensitivity": _r(sens), "specificity": _r(spec),
                "ppv": _r(ppv), "npv": _r(npv),
                "accuracy": _r(acc), "f1": _r(f1), "youden_j": _r(youden)}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════
# RELIABILITY
# ═══════════════════════════════════════════════════════════
def cronbach_alpha(items):
    """items: list of lists (each item = same length)."""
    try:
        import numpy as np
        matrix = np.array([_clean(it) for it in items])
        k = matrix.shape[0]
        n = matrix.shape[1]
        if k < 2 or n < 2: return {"error": "Need ≥ 2 items and ≥ 2 responses"}
        item_var = matrix.var(axis=1, ddof=1).sum()
        total_var = matrix.sum(axis=0).var(ddof=1)
        alpha = (k / (k - 1)) * (1 - item_var / total_var) if total_var else 0
        return {"alpha": _r(alpha), "n_items": k, "n_responses": n,
                "interpretation": ("Excellent" if alpha >= 0.9 else
                                   "Good" if alpha >= 0.8 else
                                   "Acceptable" if alpha >= 0.7 else
                                   "Questionable" if alpha >= 0.6 else
                                   "Poor")}
    except Exception as e:
        return {"error": str(e)}

# ═══════════════════════════════════════════════════════════
# SAMPLE SIZE
# ═══════════════════════════════════════════════════════════
def sample_size_mean(sd, margin, confidence=0.95):
    z = 1.96 if confidence == 0.95 else 2.576 if confidence == 0.99 else 1.645
    if margin <= 0: return {"error": "Margin must be > 0"}
    return {"n": math.ceil((z * sd / margin) ** 2),
            "formula": "n = (Z·σ / E)²",
            "confidence": confidence}

def sample_size_proportion(p, margin, confidence=0.95):
    z = 1.96 if confidence == 0.95 else 2.576 if confidence == 0.99 else 1.645
    if margin <= 0: return {"error": "Margin must be > 0"}
    return {"n": math.ceil((z ** 2 * p * (1 - p)) / margin ** 2),
            "formula": "n = Z²·p·(1−p) / E²",
            "confidence": confidence}

# ═══════════════════════════════════════════════════════════
# TREND / FORECAST
# ═══════════════════════════════════════════════════════════
def trend_forecast(values, steps=3):
    """Simple linear extrapolation of a time series."""
    x = _clean(values)
    n = len(x)
    if n < 3: return {"error": "Need ≥ 3 points"}
    xs = list(range(n))
    reg = linear_regression(xs, x)
    if reg.get("error"): return reg
    slope, intercept = reg["slope"], reg["intercept"]
    forecasts = [round(intercept + slope * (n + i), 4) for i in range(1, steps + 1)]
    return {"slope": slope, "intercept": intercept,
            "r_squared": reg["r_squared"],
            "forecast_steps": steps, "forecast_values": forecasts,
            "direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"}

def moving_average(values, window=3):
    x = _clean(values)
    if len(x) < window: return {"error": "Not enough points"}
    out = []
    for i in range(window - 1, len(x)):
        out.append(round(sum(x[i - window + 1:i + 1]) / window, 4))
    return {"window": window, "moving_averages": out}

def exponential_smoothing(values, alpha=0.3):
    x = _clean(values)
    if len(x) < 2: return {"error": "Not enough points"}
    s = x[0]
    out = [round(s, 4)]
    for v in x[1:]:
        s = alpha * v + (1 - alpha) * s
        out.append(round(s, 4))
    return {"alpha": alpha, "smoothed": out, "last_forecast": out[-1]}


# ---- Compatibility aliases ----
compare_groups = compare_auto  # backwards-compatible alias
