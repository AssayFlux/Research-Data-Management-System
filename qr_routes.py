"""QR codes — participant identification + full data payload.

Produces a compressed JSON QR containing:
  - study metadata
  - participant info
  - all parameter values
  - criteria rules
Format: RZ:<base64(zlib(json))>
"""
import io, json, base64, zlib
from flask import render_template, request, abort, send_file
from database import one, query


def _make_qr_png(text, size=6):
    """Return PNG bytes for a QR, or None if qrcode lib missing."""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # max capacity
            box_size=size, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def _build_payload(pid):
    """Build the full data payload for a participant."""
    p = one("""SELECT p.*, s.study_code, s.title AS study_title,
                      s.pi, s.institution, s.department
               FROM participants p
               JOIN studies s ON s.id = p.study_id
               WHERE p.id = ?""", (pid,))
    if not p:
        return None, None

    study_row = one("SELECT * FROM studies WHERE id=?", (p["study_id"],))

    # Values from latest record
    rec = one("""SELECT id FROM participant_records
                 WHERE participant_id = ?
                 ORDER BY id DESC LIMIT 1""", (pid,))
    rows = []
    if rec:
        rows = query("""SELECT v.numeric_value, v.value_text, v.value_state,
                               pa.code AS pcode, pa.name AS pname,
                               pa.unit, pa.category,
                               pa.ref_low, pa.ref_high, pa.ref_text
                        FROM participant_values v
                        JOIN parameters pa ON pa.id = v.parameter_id
                        WHERE v.record_id = ?
                        ORDER BY pa.sort_order""", (rec["id"],))

    criteria = query("""SELECT c.*, pa.name AS pname, pa.code AS pcode
                        FROM criteria c
                        LEFT JOIN parameters pa ON pa.id = c.parameter_id
                        WHERE c.study_id = ? AND c.active = 1
                        ORDER BY c.kind, c.sort_order, c.id""",
                     (p["study_id"],))

    # Compact JSON
    data = {
        "v": 1,
        "study": {
            "code": p["study_code"],
            "title": (study_row["title"] if study_row and "title" in study_row.keys() else ""),
            "pi": (study_row["pi"] if study_row and "pi" in study_row.keys() else ""),
            "institution": (study_row["institution"] if study_row and "institution" in study_row.keys() else ""),
            "department": (study_row["department"] if study_row and "department" in study_row.keys() else ""),
        },
        "participant": {
            "code": p["participant_code"],
            "age": p["age"],
            "sex": p["sex"] or "",
            "consent": p["consent_status"] or "",
            "visit_date": p["visit_date"] or "",
            "group_type": p["group_type"] or "",
            "classification": (p["classification"] if "classification" in p.keys() and p["classification"] else "Undetermined"),
            "reason": (p["classification_reason"] if "classification_reason" in p.keys() else "") or "",
        },
        "values": [],
        "criteria": [],
    }

    for r in rows:
        data["values"].append({
            "c": r["pcode"],
            "n": r["pname"],
            "u": r["unit"] or "",
            "cat": r["category"] or "",
            "v": r["numeric_value"] if r["numeric_value"] is not None else r["value_text"],
            "lo": r["ref_low"],
            "hi": r["ref_high"],
            "rt": r["ref_text"] or "",
            "s": r["value_state"],
        })

    for c in criteria:
        data["criteria"].append({
            "k": c["kind"],
            "n": c["name"],
            "op": c["operator"],
            "v1": c["value1"] or "",
            "v2": c["value2"] or "",
        })

    json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    try:
        compressed = zlib.compress(json_str.encode("utf-8"), 9)
        b64 = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
        text = f"RZ:{b64}"
    except Exception:
        text = json_str

    return p, text


def register(app):

    @app.route("/participant/<int:pid>/qr")
    def qr_page(pid):
        p, text = _build_payload(pid)
        if not p:
            abort(404)
        # Show preview info
        data_size = len(text)
        fits = data_size < 2900
        return render_template("qr_page.html",
                               p=p, qr_text=text,
                               data_size=data_size,
                               fits=fits)

    @app.route("/participant/<int:pid>/qr.png")
    def qr_png(pid):
        p, text = _build_payload(pid)
        if not p:
            abort(404)
        size = max(3, min(10, request.args.get("size", 5, type=int)))
        blob = _make_qr_png(text, size)
        if not blob:
            abort(503, "qrcode library not installed. Run: pip install 'qrcode[pil]'")
        return send_file(io.BytesIO(blob),
                         mimetype="image/png",
                         download_name=f"{p['participant_code']}_qr.png")
