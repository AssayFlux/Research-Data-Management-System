"""Critical value rule evaluation."""


def _apply(op, actual, v1, v2):
    try:
        a = float(actual)
    except (TypeError, ValueError):
        return False
    try:
        n1 = float(v1) if v1 is not None else None
        n2 = float(v2) if v2 is not None else None
    except (TypeError, ValueError):
        return False
    if op == "gt":  return n1 is not None and a >  n1
    if op == "gte": return n1 is not None and a >= n1
    if op == "lt":  return n1 is not None and a <  n1
    if op == "lte": return n1 is not None and a <= n1
    if op == "eq":  return n1 is not None and a == n1
    if op == "between":
        return n1 is not None and n2 is not None and n1 <= a <= n2
    return False


def evaluate_record(record_id):
    """Run all active rules against values in a record. Insert alerts."""
    from database import query, execute
    rules = query("""SELECT r.*, p.name AS pname, p.code AS pcode, p.unit
                     FROM critical_rules r
                     JOIN parameters p ON p.id = r.parameter_id
                     WHERE r.active = 1""")
    if not rules:
        return 0
    vals = query("""SELECT v.*, r.participant_id FROM participant_values v
                    JOIN participant_records r ON r.id = v.record_id
                    WHERE v.record_id = ?""", (record_id,))
    lookup = {v["parameter_id"]: v for v in vals}
    participant_id = vals[0]["participant_id"] if vals else None
    count = 0
    for rule in rules:
        v = lookup.get(rule["parameter_id"])
        if not v or v["numeric_value"] is None:
            continue
        if _apply(rule["operator"], v["numeric_value"], rule["value1"], rule["value2"]):
            msg = rule["message"] or (
                f"{rule['pname']} = {v['numeric_value']} "
                f"{rule['unit'] or ''} (threshold {rule['operator']} "
                f"{rule['value1']})")
            # dedupe: skip if same alert already exists
            exists = query("""SELECT id FROM alerts WHERE record_id = ?
                              AND rule_id = ? AND acknowledged = 0""",
                           (record_id, rule["id"]))
            if exists:
                continue
            execute("""INSERT INTO alerts
                       (participant_id, parameter_id, record_id, rule_id,
                        severity, message)
                       VALUES(?,?,?,?,?,?)""",
                    (participant_id, rule["parameter_id"], record_id,
                     rule["id"], rule["severity"], msg))
            count += 1
    return count


def run_all(study_id=None):
    """Scan all records in a study (or everywhere) for alerts."""
    from database import query, execute
    sql = "SELECT id FROM participant_records"
    args = []
    if study_id:
        sql = """SELECT r.id FROM participant_records r
                 JOIN participants p ON p.id = r.participant_id
                 WHERE p.study_id = ?"""
        args = [study_id]
    recs = query(sql, args)
    total = 0
    for r in recs:
        total += evaluate_record(r["id"])
    return total
