"""Criteria evaluation and participant classification engine.

Designed to accept sqlite3.Row, dict, and mapping-like rule objects.
Never calls .get() directly on sqlite3.Row.
"""

from collections.abc import Mapping


def _field(obj, key, default=None):
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    try:
        return obj[key]
    except (KeyError, IndexError, TypeError):
        return default


def _to_num(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _apply_op(op, actual, v1=None, v2=None):
    op = (op or "").strip().lower()
    if actual is None or actual == "":
        if op == "empty": return True, "value is empty"
        if op == "exists": return False, "value is missing"
        return None, "value missing — cannot evaluate"

    n_actual = _to_num(actual)
    n1 = _to_num(v1); n2 = _to_num(v2)
    try:
        if op == "gt": return (n_actual is not None and n1 is not None and n_actual > n1), f"{actual} > {v1}"
        if op == "gte": return (n_actual is not None and n1 is not None and n_actual >= n1), f"{actual} ≥ {v1}"
        if op == "lt": return (n_actual is not None and n1 is not None and n_actual < n1), f"{actual} < {v1}"
        if op == "lte": return (n_actual is not None and n1 is not None and n_actual <= n1), f"{actual} ≤ {v1}"
        if op == "eq": return str(actual) == str(v1), f"{actual} = {v1}"
        if op == "neq": return str(actual) != str(v1), f"{actual} ≠ {v1}"
        if op == "between": return (n_actual is not None and n1 is not None and n2 is not None and n1 <= n_actual <= n2), f"{v1} ≤ {actual} ≤ {v2}"
        if op == "in": return str(actual) in [x.strip() for x in str(v1 or "").split(",")], f"{actual} in {v1}"
        if op == "not_in": return str(actual) not in [x.strip() for x in str(v1 or "").split(",")], f"{actual} not in {v1}"
        if op == "contains": return str(v1 or "").lower() in str(actual).lower(), f"{actual} contains {v1}"
        if op == "not_contains": return str(v1 or "").lower() not in str(actual).lower(), f"{actual} doesn't contain {v1}"
        if op == "yes": return str(actual).strip().lower() in ("yes", "1", "true", "y"), f"is yes ({actual})"
        if op == "no": return str(actual).strip().lower() in ("no", "0", "false", "n"), f"is no ({actual})"
        if op == "exists": return True, "value exists"
        if op == "empty": return False, "value not empty"
    except Exception as exc:
        return None, f"evaluation error: {exc}"
    return None, f"unknown operator '{op}'"


def evaluate_rule(rule, value):
    """Evaluate a criterion rule. Works with sqlite3.Row as well as dict."""
    op = _field(rule, "operator", "")
    v1 = _field(rule, "value1")
    v2 = _field(rule, "value2")
    return _apply_op(op, value, v1, v2)


def _safe_all_pass(details):
    return bool(details) and all(d["passed"] is True for d in details)


def _group_eval(rules, lookup_by_id):
    """Evaluate a rule group and return (all_pass, details).

    lookup_by_id may contain raw values or (raw_value, value_state) tuples.
    sqlite3.Row rules are fully supported.
    """
    details = []
    for rule in rules or []:
        pid = _field(rule, "parameter_id")
        item = lookup_by_id.get(pid) if hasattr(lookup_by_id, "get") else None
        if isinstance(item, tuple) and len(item) >= 1:
            actual = item[0]
        else:
            actual = item
        passed, msg = evaluate_rule(rule, actual)
        details.append({
            "rule": _field(rule, "name", f"Rule {pid}"),
            "parameter_id": pid,
            "passed": passed,
            "message": msg,
        })
    return _safe_all_pass(details), details


def classify_participant(participant_id):
    from database import query, one
    p = one("SELECT * FROM participants WHERE id=?", (participant_id,))
    if not p:
        return "Undetermined", "participant not found", []

    rec = one("SELECT id FROM participant_records WHERE participant_id=? ORDER BY id DESC LIMIT 1", (participant_id,))
    if not rec:
        return "Undetermined", "no data recorded yet", []

    vals = query("SELECT parameter_id, value_text, numeric_value, value_state FROM participant_values WHERE record_id=?", (rec["id"],))
    lookup = {}
    for v in vals:
        raw = v["numeric_value"] if v["numeric_value"] is not None else v["value_text"]
        lookup[v["parameter_id"]] = (raw, v["value_state"])

    rules = query("SELECT * FROM criteria WHERE active=1 AND (study_id=? OR study_id IS NULL) ORDER BY kind, sort_order, id", (p["study_id"],))
    by_kind = {"inclusion": [], "exclusion": [], "control": [], "study": []}
    for r in rules:
        kind = _field(r, "kind", "")
        if kind in by_kind:
            by_kind[kind].append(r)

    def eval_kind(kind):
        return _group_eval(by_kind[kind], lookup)

    inc_all, inc_details = eval_kind("inclusion")
    if by_kind["inclusion"] and not inc_all:
        failed = [d["rule"] for d in inc_details if d["passed"] is False]
        unknown = [d["rule"] for d in inc_details if d["passed"] is None]
        if unknown and not failed:
            return "Undetermined", "Inclusion criteria contain missing/unknown values", inc_details
        reason = "Failed inclusion criteria: " + "; ".join(failed)[:200]
        return "Excluded", reason, inc_details

    exc_all, exc_details = eval_kind("exclusion")
    if by_kind["exclusion"]:
        if any(d["passed"] is True for d in exc_details):
            met = [d["rule"] for d in exc_details if d["passed"] is True]
            return "Excluded", "Met exclusion criteria: " + "; ".join(met)[:200], inc_details + exc_details
        if any(d["passed"] is None for d in exc_details):
            return "Undetermined", "Exclusion criteria contain missing/unknown values", inc_details + exc_details

    ctrl_all, ctrl_details = eval_kind("control")
    if by_kind["control"] and ctrl_all:
        return "Control", "Matched control criteria", inc_details + exc_details + ctrl_details

    study_all, study_details = eval_kind("study")
    if by_kind["study"] and study_all:
        return "Study", "Matched study criteria", inc_details + exc_details + ctrl_details + study_details

    if not any(by_kind.values()):
        g = (p["group_type"] or "").lower()
        if "control" in g: return "Control", "from participant group", []
        if "case" in g or "study" in g: return "Study", "from participant group", []

    return "Undetermined", "no classification rules matched", inc_details + exc_details + ctrl_details + study_details
