"""Inter-rater reliability — Cohen's kappa, weighted kappa, ICC(2,1), ICC(3,1)."""
import math


def _clean(x):
    out = []
    for v in x:
        if v is None or v == "": continue
        out.append(v)
    return out


def _mean(x): return sum(x) / len(x) if x else 0


def _stdev(x):
    if len(x) < 2: return 0
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def cohens_kappa(rater1, rater2):
    """Cohen's kappa for two raters, categorical labels."""
    pairs = [(str(a), str(b)) for a, b in zip(rater1, rater2)
             if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return {"error": "No paired observations"}
    cats = sorted(set(a for a, _ in pairs) | set(b for _, b in pairs))
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    matrix = [[0]*k for _ in range(k)]
    for a, b in pairs:
        matrix[idx[a]][idx[b]] += 1
    # observed agreement
    po = sum(matrix[i][i] for i in range(k)) / n
    # expected agreement
    row = [sum(matrix[i][j] for j in range(k)) for i in range(k)]
    col = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
    pe = sum(row[i] * col[i] for i in range(k)) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe != 1 else 0
    interpretation = ("Poor" if kappa < 0 else
                      "Slight" if kappa < 0.20 else
                      "Fair" if kappa < 0.40 else
                      "Moderate" if kappa < 0.60 else
                      "Substantial" if kappa < 0.80 else
                      "Almost perfect")
    return {"metric": "Cohen's kappa",
            "kappa": round(kappa, 4),
            "observed_agreement": round(po, 4),
            "expected_agreement": round(pe, 4),
            "n": n, "k_categories": k,
            "interpretation": interpretation,
            "matrix": matrix, "categories": cats}


def weighted_kappa(rater1, rater2, weights="linear"):
    """Weighted kappa for ordinal ratings."""
    pairs = [(float(a), float(b)) for a, b in zip(rater1, rater2)
             if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return {"error": "No paired observations"}
    cats = sorted(set(a for a, _ in pairs) | set(b for _, b in pairs))
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    if k < 2:
        return {"error": "Need at least 2 rating categories"}
    matrix = [[0]*k for _ in range(k)]
    for a, b in pairs:
        matrix[idx[a]][idx[b]] += 1
    row = [sum(matrix[i][j] for j in range(k)) for i in range(k)]
    col = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
    n_total = float(n)

    def w(i, j):
        d = abs(i - j) / (k - 1)
        return d if weights == "linear" else d * d

    po_w = sum(w(i, j) * matrix[i][j] for i in range(k) for j in range(k)) / n_total
    pe_w = sum(w(i, j) * row[i] * col[j] for i in range(k) for j in range(k)) / (n_total * n_total)
    kappa_w = 1 - po_w / pe_w if pe_w > 0 else 0
    return {"metric": f"Weighted kappa ({weights})",
            "kappa": round(kappa_w, 4),
            "n": n, "k_categories": k,
            "weights": weights}


def icc_2_1(ratings):
    """ICC(2,1) — two-way random effects, absolute agreement, single measures.
    ratings: list of subjects, each is a list of ratings from multiple raters."""
    ratings = [r for r in ratings if len(r) >= 2]
    n = len(ratings)         # subjects
    k = min(len(r) for r in ratings)  # raters
    if n < 2 or k < 2:
        return {"error": "Need ≥ 2 subjects × ≥ 2 raters"}
    data = [r[:k] for r in ratings]
    grand = _mean([v for r in data for v in r])
    row_means = [_mean(r) for r in data]
    col_means = [_mean([data[i][j] for i in range(n)]) for j in range(k)]
    ss_total = sum((v - grand) ** 2 for r in data for v in r)
    ss_rows = k * sum((rm - grand) ** 2 for rm in row_means)
    ss_cols = n * sum((cm - grand) ** 2 for cm in col_means)
    ss_err = ss_total - ss_rows - ss_cols
    ms_rows = ss_rows / (n - 1) if n > 1 else 0
    ms_cols = ss_cols / (k - 1) if k > 1 else 0
    ms_err = ss_err / ((n - 1) * (k - 1)) if (n > 1 and k > 1) else 0
    # ICC(2,1) absolute agreement
    denom = ms_rows + (k - 1) * ms_err + k * (ms_cols - ms_err) / n
    icc = (ms_rows - ms_err) / denom if denom != 0 else 0
    return {"metric": "ICC(2,1) absolute agreement",
            "icc": round(icc, 4), "n_subjects": n, "k_raters": k,
            "interpretation": _icc_label(icc)}


def icc_3_1(ratings):
    """ICC(3,1) — two-way mixed, consistency, single measures."""
    ratings = [r for r in ratings if len(r) >= 2]
    n = len(ratings); k = min(len(r) for r in ratings)
    if n < 2 or k < 2:
        return {"error": "Need ≥ 2 subjects × ≥ 2 raters"}
    data = [r[:k] for r in ratings]
    grand = _mean([v for r in data for v in r])
    row_means = [_mean(r) for r in data]
    ss_total = sum((v - grand) ** 2 for r in data for v in r)
    ss_rows = k * sum((rm - grand) ** 2 for rm in row_means)
    ss_err = ss_total - ss_rows
    ms_rows = ss_rows / (n - 1) if n > 1 else 0
    ms_err = ss_err / ((n - 1) * (k - 1)) if (n > 1 and k > 1) else 0
    icc = (ms_rows - ms_err) / (ms_rows + (k - 1) * ms_err) if ms_rows != 0 else 0
    return {"metric": "ICC(3,1) consistency",
            "icc": round(icc, 4), "n_subjects": n, "k_raters": k,
            "interpretation": _icc_label(icc)}


def _icc_label(v):
    if v < 0.5: return "Poor"
    if v < 0.75: return "Moderate"
    if v < 0.9: return "Good"
    return "Excellent"


def bland_altman(m1, m2):
    """Bland-Altman limits of agreement."""
    diffs = [a - b for a, b in zip(m1, m2) if a is not None and b is not None]
    n = len(diffs)
    if n < 2:
        return {"error": "Need ≥ 2 paired measurements"}
    mean_diff = _mean(diffs)
    sd_diff = _stdev(diffs)
    return {"metric": "Bland-Altman",
            "mean_difference": round(mean_diff, 4),
            "sd_difference": round(sd_diff, 4),
            "lower_loa": round(mean_diff - 1.96 * sd_diff, 4),
            "upper_loa": round(mean_diff + 1.96 * sd_diff, 4),
            "n": n}
