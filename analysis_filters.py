"""Central value-fetch with classification + records-mode filters.
Used by statistics, graphs, print, and query builder."""

VALID_MODES    = ("all", "latest", "first", "last_visit")
VALID_CLASSES  = ("", "Study", "Control", "Excluded", "Undetermined")


def _build_sql(parameter_ids, study_id=None, classification=None, mode="latest"):
    """Return (sql, args). Each row: participant_id, parameter_id, numeric_value,
    value_text, value_state, group_type, classification, participant_code,
    visit_date, record_id."""
    sql = """SELECT v.numeric_value, v.value_text, v.value_state,
                    v.parameter_id, r.id AS record_id, r.visit_date,
                    p.id AS participant_id, p.participant_code,
                    p.group_type, p.classification, p.study_id,
                    s.study_code
             FROM participant_values v
             JOIN participant_records r ON r.id = v.record_id
             JOIN participants p ON p.id = r.participant_id
             JOIN studies s ON s.id = p.study_id
             WHERE v.parameter_id IN ({placeholders})
               AND p.archived = 0"""
    args = list(parameter_ids)
    ph = ",".join("?" for _ in parameter_ids)
    sql = sql.replace("{placeholders}", ph)

    if study_id:
        sql += " AND p.study_id = ?"
        args.append(study_id)
    if classification in ("Study", "Control", "Excluded", "Undetermined"):
        sql += " AND (p.classification = ? OR (p.classification IS NULL AND ? = 'Undetermined'))"
        args += [classification, classification]

    sql += " ORDER BY p.id, r.visit_date, r.id"
    return sql, args


def _pick_per_participant(rows, mode):
    """rows: list of sqlite Row. Returns filtered list of rows per mode.

    Modes:
      all        → every row
      latest     → rows from the highest record_id per participant
      first      → rows from the lowest record_id per participant
      last_visit → rows from the most recent visit_date (falls back to record_id)
    """
    if mode == "all":
        return rows
    by_part = {}
    for r in rows:
        by_part.setdefault(r["participant_id"], []).append(r)

    out = []
    for pid, recs in by_part.items():
        by_rec = {}
        for r in recs:
            by_rec.setdefault(r["record_id"], []).append(r)

        if mode == "first":
            chosen = min(by_rec.keys())
        elif mode == "last_visit":
            # Sort by visit_date then record_id; pick the max
            def _key(rid):
                sample = by_rec[rid][0]
                return (sample["visit_date"] or "", rid)
            chosen = max(by_rec.keys(), key=_key)
        else:  # latest
            chosen = max(by_rec.keys())

        out.extend(by_rec[chosen])
    return out


def fetch_values(parameter_ids, study_id=None, classification=None, mode="latest"):
    """High-level: returns a list of Row with the filters applied."""
    from database import query
    if not parameter_ids:
        return []
    sql, args = _build_sql(parameter_ids, study_id, classification, mode)
    rows = query(sql, args)
    return _pick_per_participant(rows, mode)


def fetch_single(parameter_id, study_id=None, classification=None, mode="latest"):
    """Numeric values for a single parameter."""
    rows = fetch_values([parameter_id], study_id, classification, mode)
    return [r["numeric_value"] for r in rows
            if r["value_state"] == "VALUE" and r["numeric_value"] is not None]


def fetch_paired(x_id, y_id, study_id=None, classification=None, mode="latest"):
    """Aligned (x, y) pairs for correlation / regression."""
    rows = fetch_values([x_id, y_id], study_id, classification, mode)
    by_rec = {}
    for r in rows:
        if r["value_state"] != "VALUE" or r["numeric_value"] is None:
            continue
        by_rec.setdefault(r["record_id"], {})[r["parameter_id"]] = r["numeric_value"]
    xs, ys = [], []
    for d in by_rec.values():
        if x_id in d and y_id in d:
            xs.append(d[x_id]); ys.append(d[y_id])
    return xs, ys


def groups_by_classification(parameter_id, study_id=None, mode="latest",
                             use_classification=True):
    """Group values by classification (default) or by group_type."""
    rows = fetch_values([parameter_id], study_id, None, mode)
    groups = {}
    for r in rows:
        if r["value_state"] != "VALUE" or r["numeric_value"] is None:
            continue
        key = (r["classification"] if use_classification and r["classification"]
               else r["group_type"] or "Unclassified")
        groups.setdefault(key, []).append(r["numeric_value"])
    return groups


def formulas_for_parameter(parameter_id):
    """Return formulas whose output is this parameter (for print footnote)."""
    from database import query
    return query("""SELECT f.id, f.name, f.code, f.expression, f.description
                    FROM formulas f
                    WHERE f.output_parameter_id = ? AND f.active = 1""",
                 (parameter_id,))


def formula_input_codes(formula_id):
    from database import query
    return [r["code"] for r in query("""
        SELECT p.code FROM formula_inputs fi
        JOIN parameters p ON p.id = fi.parameter_id
        WHERE fi.formula_id = ? ORDER BY p.code""", (formula_id,))]
