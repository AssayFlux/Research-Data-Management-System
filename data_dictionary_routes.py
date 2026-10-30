"""Data dictionary — export schema as CSV/XLSX/PDF."""
import io
from datetime import datetime
from flask import render_template, request, send_file, abort
from database import query, one
from export import csv_bytes, xlsx_bytes, pdf_bytes

HEADERS = ["Code","Name","Category","Group","Data type","Unit",
           "Ref low","Ref high","Ref text","Choices","Required","Description"]


def _rows(params):
    out = []
    for p in params:
        out.append([
            p["code"], p["name"], p["category"] or "",
            p["group_name"] or "", p["data_type"] or "", p["unit"] or "",
            p["ref_low"] if p["ref_low"] is not None else "",
            p["ref_high"] if p["ref_high"] is not None else "",
            p["ref_text"] or "", p["choices"] or "",
            "Yes" if p["required"] else "No",
            p["description"] or "",
        ])
    return out


def register(app):

    @app.route("/data-dictionary")
    def data_dictionary_page():
        study_id = request.args.get("study_id", type=int)
        study = one("SELECT * FROM studies WHERE id=?", (study_id,)) if study_id else None
        params = query("""SELECT p.*, g.name AS group_name
                          FROM parameters p
                          LEFT JOIN parameter_groups g ON g.id=p.group_id
                          WHERE p.active=1 ORDER BY p.category, p.sort_order, p.name""")
        formulas = query("""SELECT f.*, p.code AS output_code, p.name AS output_name
                            FROM formulas f LEFT JOIN parameters p ON p.id=f.output_parameter_id
                            WHERE f.active=1 ORDER BY f.name""")
        studies = query("SELECT id,study_code,title FROM studies WHERE archived=0 ORDER BY title")
        return render_template("data_dictionary.html", params=params,
                               formulas=formulas, study=study, studies=studies)

    @app.route("/data-dictionary/export/<fmt>")
    def data_dictionary_export(fmt):
        study_id = request.args.get("study_id", type=int)
        study = one("SELECT * FROM studies WHERE id=?", (study_id,)) if study_id else None
        params = query("""SELECT p.*, g.name AS group_name
                          FROM parameters p
                          LEFT JOIN parameter_groups g ON g.id=p.group_id
                          WHERE p.active=1 ORDER BY p.category, p.sort_order, p.name""")
        rows = _rows(params)
        title = "Data Dictionary" + (f" — {study['study_code']}" if study else "")
        sub = f"{len(rows)} parameters · {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if fmt == "csv":
            blob = csv_bytes(HEADERS, rows); mt = "text/csv"; name = "data_dictionary.csv"
        elif fmt == "xlsx":
            blob = xlsx_bytes(HEADERS, rows, "Data Dictionary")
            mt = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            name = "data_dictionary.xlsx"
        elif fmt == "pdf":
            blob = pdf_bytes(title, HEADERS, rows, sub); mt = "application/pdf"; name = "data_dictionary.pdf"
        else:
            abort(404)
        return send_file(io.BytesIO(blob), download_name=name,
                         as_attachment=True, mimetype=mt)
