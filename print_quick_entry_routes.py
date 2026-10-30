"""Quick Entry print — dedicated one-page report with QR code."""
import io, json, base64
from functools import wraps
from flask import render_template, abort, g, send_file, request, jsonify, url_for
from database import query, one

# Parameter categories → display group titles
CATEGORY_GROUP = {
    "Demographic":    "BASELINE",
    "Anthropometric": "ANTHROPOMETRIC",
    "Vitals":         "VITALS",
    "Biochemical":    "LAB",
    "Hematology":     "LAB - INFLAMMATORY & HEMATOLOGY",
    "Coagulation":    "LAB - COAGULATION",
    "Endocrine":      "LAB - HORMONAL",
    "Urine":          "URINE ANALYSIS",
    "Clinical":       "CLINICAL",
    "Other":          "OTHER",
}


def _status_for(value, ref_low, ref_high, ref_text, dtype):
    """Return (status, code) where status is 'High'/'Low'/'Normal'/'—'."""
    if value is None or value == "":
        return "—", "none"
    if dtype not in ("Integer", "Decimal"):
        return "—", "none"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—", "none"

    lo = ref_low if ref_low is not None else None
    hi = ref_high if ref_high is not None else None

    if lo is not None and v < lo:
        return "Low", "low"
    if hi is not None and v > hi:
        return "High", "high"
    if lo is None and hi is None:
        return "—", "none"
    return "Normal", "normal"


def _fmt_ref(ref_low, ref_high, ref_text):
    if ref_text:
        return ref_text
    if ref_low is not None and ref_high is not None:
        return f"{ref_low} – {ref_high}"
    if ref_low is not None:
        return f"≥ {ref_low}"
    if ref_high is not None:
        return f"≤ {ref_high}"
    return "—"


def _fmt_val(value, numeric_value, dtype):
    if value is None and numeric_value is None:
        return "—"
    if numeric_value is not None:
        if dtype == "Integer":
            return str(int(numeric_value))
        # Trim trailing zeros: 3.460 → 3.46
        if float(numeric_value).is_integer():
            return str(int(numeric_value))
        return f"{numeric_value:.4g}"
    return str(value)


def _build_qr_payload(p, study, values_list, criteria=None, groups=None):
    """Full participant data for QR — everything needed to reconstruct."""
    data = {
        "v": 1,
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "study": {
            "code": study["study_code"],
            "title": study.get("title", "") if hasattr(study, "get") else (study["title"] if "title" in study.keys() else ""),
            "pi": study.get("pi", "") if hasattr(study, "get") else (study["pi"] if "pi" in study.keys() else ""),
            "institution": study.get("institution", "") if hasattr(study, "get") else (study["institution"] if "institution" in study.keys() else ""),
            "department": study.get("department", "") if hasattr(study, "get") else (study["department"] if "department" in study.keys() else ""),
        },
        "participant": {
            "code": p["participant_code"],
            "age": p["age"],
            "sex": p["sex"] or "",
            "consent": p["consent_status"] or "",
            "visit_date": p["visit_date"] or "",
            "group_type": p["group_type"] or "",
            "classification": (p["classification"] if "classification" in p.keys() and p["classification"] else "Undetermined"),
            "classification_reason": (p["classification_reason"] if "classification_reason" in p.keys() else "") or "",
        },
        "values": [],
        "criteria": [],
    }

    # Full values
    for row in values_list:
        data["values"].append({
            "code": row["pcode"],
            "name": row["pname"],
            "unit": row["unit"] or "",
            "category": row["category"] or "",
            "value": row["numeric_value"] if row["numeric_value"] is not None else row["value_text"],
            "ref_low": row["ref_low"],
            "ref_high": row["ref_high"],
            "ref_text": row["ref_text"] or "",
            "state": row["value_state"],
        })

    # Criteria results
    if criteria:
        for c in criteria:
            data["criteria"].append({
                "kind": c["kind"],
                "name": c["name"],
                "operator": c["operator"],
                "value1": c["value1"],
                "value2": c["value2"],
            })

    return data


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

    # ═══════════════════════════════════════════════════════════
    # QR PNG — encodes participant data
    # ═══════════════════════════════════════════════════════════
    @app.route("/print/quick-entry/qr/<int:pid>.png")
    @role_required("ADMIN", "RESEARCHER")
    def quick_entry_qr_png(pid):
        p = one("""SELECT p.*, s.study_code, s.title AS study_title
                   FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)

        # Fetch all values
        rows = query("""SELECT v.numeric_value, v.value_text, v.value_state,
                               pa.code AS pcode
                        FROM participant_values v
                        JOIN participant_records r ON r.id = v.record_id
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE r.participant_id = ?
                        ORDER BY pa.sort_order""", (pid,))

        study_row = one("SELECT * FROM studies WHERE id=?", (p["study_id"],))
        criteria = query("""SELECT c.*, pa.name AS pname, pa.code AS pcode
                            FROM criteria c
                            LEFT JOIN parameters pa ON pa.id = c.parameter_id
                            WHERE c.study_id = ? AND c.active = 1
                            ORDER BY c.kind, c.sort_order, c.id""",
                         (p["study_id"],))
        payload = _build_qr_payload(p, study_row, rows, criteria)
        json_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

        # Compress with zlib then base64url encode — fits in a QR code
        try:
            import zlib
            compressed = zlib.compress(json_str.encode("utf-8"), 9)
            encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
            data = f"RZ:{encoded}"
        except Exception:
            data = json_str

        # Show size for debugging (visible in Termux console)
        print(f"[qr] participant {pid}: raw={len(json_str)} compressed={len(data)}")

        size = max(3, min(10, request.args.get("size", 6, type=int)))

        try:
            import qrcode
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0f172a", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return send_file(io.BytesIO(buf.getvalue()),
                             mimetype="image/png",
                             download_name=f"{p['participant_code']}_qr.png")
        except ImportError:
            abort(503, "qrcode library not installed")
        except Exception as e:
            abort(500, str(e))

    # ═══════════════════════════════════════════════════════════
    # Data viewer (in case someone decodes the QR manually)
    # ═══════════════════════════════════════════════════════════
    @app.route("/print/quick-entry/data/<int:pid>")
    @role_required("ADMIN", "RESEARCHER")
    def quick_entry_data_view(pid):
        p = one("""SELECT p.*, s.study_code, s.title AS study_title
                   FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)

        rows = query("""SELECT v.numeric_value, v.value_text, v.value_state,
                               pa.code AS pcode, pa.name AS pname
                        FROM participant_values v
                        JOIN participant_records r ON r.id = v.record_id
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE r.participant_id = ?
                        ORDER BY pa.sort_order""", (pid,))

        study_row = one("SELECT * FROM studies WHERE id=?", (p["study_id"],))
        payload = _build_qr_payload(p, study_row, rows)
        return jsonify(payload)

    # ═══════════════════════════════════════════════════════════
    # MAIN PRINT PAGE
    # ═══════════════════════════════════════════════════════════
    @app.route("/print/quick-entry/<int:pid>")
    @role_required("ADMIN", "RESEARCHER")
    def print_quick_entry(pid):
        p = one("""SELECT p.*, s.study_code, s.title AS study_title,
                          s.pi, s.institution, s.department,
                          s.protocol_no, s.ethics_no,
                          s.frozen, s.freeze_reason, s.cutoff_date
                   FROM participants p
                   JOIN studies s ON s.id = p.study_id
                   WHERE p.id = ?""", (pid,))
        if not p: abort(404)

        # Fetch latest record
        rec = one("""SELECT * FROM participant_records
                     WHERE participant_id = ? ORDER BY id DESC LIMIT 1""", (pid,))

        # Fetch all values from the latest record
        values = []
        if rec:
            values = query("""SELECT v.*, pa.code AS pcode, pa.name AS pname,
                                     pa.unit, pa.category, pa.data_type,
                                     pa.ref_low, pa.ref_high, pa.ref_text,
                                     pa.sort_order,
                                     (SELECT COUNT(*) FROM formulas f
                                      WHERE f.output_parameter_id = pa.id
                                        AND f.active = 1) AS is_auto
                              FROM participant_values v
                              JOIN parameters pa ON pa.id = v.parameter_id
                              WHERE v.record_id = ?
                              ORDER BY pa.sort_order, pa.name""", (rec["id"],))

        # Build category groups
        by_cat = {}
        for v in values:
            cat = v["category"] or "Other"
            by_cat.setdefault(cat, []).append(v)

        # Order: Demographic, Anthropometric, Vitals, Biochemical, Hematology,
        # Coagulation, Endocrine, Urine, Clinical, Other
        category_order = ["Demographic", "Anthropometric", "Vitals",
                          "Biochemical", "Hematology", "Coagulation",
                          "Endocrine", "Urine", "Clinical", "Other"]

        groups = []
        high_count = low_count = normal_count = none_count = 0

        for cat in category_order:
            if cat not in by_cat: continue
            items = by_cat[cat]
            params_display = []
            for v in items:
                status_label, status_code = _status_for(
                    v["numeric_value"] if v["numeric_value"] is not None else v["value_text"],
                    v["ref_low"], v["ref_high"], v["ref_text"], v["data_type"]
                )
                if status_code == "high": high_count += 1
                elif status_code == "low": low_count += 1
                elif status_code == "normal": normal_count += 1
                else: none_count += 1

                # Add "(auto)" suffix for formula outputs
                name_display = v["pname"]
                if v["is_auto"]:
                    name_display += " (auto)"

                params_display.append({
                    "code": v["pcode"],
                    "name": name_display,
                    "value": _fmt_val(v["value_text"], v["numeric_value"], v["data_type"]),
                    "unit": v["unit"] or "",
                    "ref": _fmt_ref(v["ref_low"], v["ref_high"], v["ref_text"]),
                    "status": status_label,
                    "status_code": status_code,
                })
            groups.append({
                "title": CATEGORY_GROUP.get(cat, cat.upper()),
                "original_category": cat,
                "params": params_display,
            })

        total_params = sum(len(g["params"]) for g in groups)

        # Criteria results
        criteria = query("""SELECT c.*, pa.name AS pname, pa.code AS pcode
                            FROM criteria c
                            LEFT JOIN parameters pa ON pa.id = c.parameter_id
                            WHERE c.study_id = ? AND c.active = 1
                            ORDER BY c.kind, c.sort_order, c.id""",
                         (p["study_id"],))

        # Build criteria summary with pass/fail
        # Build value map
        value_map = {v["parameter_id"]: (v["numeric_value"] if v["numeric_value"] is not None else v["value_text"])
                     for v in values}

        crit_by_kind = {"inclusion": [], "exclusion": [], "control": [], "study": []}
        for c in criteria:
            actual = value_map.get(c["parameter_id"])
            passed = None
            if actual is not None:
                try:
                    a = float(actual)
                    v1 = float(c["value1"]) if c["value1"] else None
                    v2 = float(c["value2"]) if c["value2"] else None
                    op = c["operator"]
                    if op == "gt":  passed = a > v1 if v1 is not None else None
                    elif op == "gte": passed = a >= v1 if v1 is not None else None
                    elif op == "lt":  passed = a < v1 if v1 is not None else None
                    elif op == "lte": passed = a <= v1 if v1 is not None else None
                    elif op == "eq":  passed = str(actual) == str(c["value1"])
                    elif op == "neq": passed = str(actual) != str(c["value1"])
                    elif op == "between":
                        passed = v1 <= a <= v2 if (v1 is not None and v2 is not None) else None
                    elif op == "in":
                        passed = str(actual) in [x.strip() for x in (c["value1"] or "").split(",")]
                    elif op == "not_in":
                        passed = str(actual) not in [x.strip() for x in (c["value1"] or "").split(",")]
                    elif op == "yes": passed = str(actual).lower() in ("yes","1","true")
                    elif op == "no":  passed = str(actual).lower() in ("no","0","false")
                except (ValueError, TypeError):
                    passed = None

            crit_by_kind[c["kind"]].append({
                "name": c["name"],
                "op": c["operator"],
                "v1": c["value1"] or "",
                "v2": c["value2"] or "",
                "pname": c["pname"] or "",
                "passed": passed,
            })

        # QR URL for this participant
        qr_url = url_for("quick_entry_qr_png", pid=pid, size=5)

        # Print config
        from print_settings import get_profile
        cfg = get_profile("quick_entry")

        return render_template("print_quick_entry.html",
                               p=p, rec=rec, groups=groups,
                               total_params=total_params,
                               high_count=high_count,
                               low_count=low_count,
                               normal_count=normal_count,
                               none_count=none_count,
                               crit_by_kind=crit_by_kind,
                               qr_url=qr_url,
                               cfg=cfg)
