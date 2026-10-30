"""Print settings — profiles for header, footer, signatures, extras."""
import json
from database import one, execute, query
from config import APP_NAME

CONTEXTS = {
    "default":              "Global default",
    "participant":          "Participant sheet",
    "study":                "Study summary",
    "records":              "Records list",
    "statistics":           "Statistics report",
    "participants_summary": "Participants summary",
    "quick_entry":          "Quick Entry sheet",
    "parameter_summary":    "Parameter summary",
    "group_comparison":     "Group comparison",
    "study_progress":       "Study progress",
    "quality_report":       "Data quality report",
    "blank_form":           "Blank data form",
}

DEFAULT_PROFILE = {
    "institution": "",
    "subtitle":    "",
    "department":  "",
    "study_name":  "",
    "header_lines": [],
    "guides":      [],
    "coguides":    [],
    "researchers": [],
    "signatures":  ["Guide", "Co-Guide", "Researcher"],
    "copyright":   f"© {APP_NAME}",
    "website":     "",
    "footer_lines": [],
    "logo_url":    "",
    "show_logo":   False,
    "show_signatures": True,
    "extra_enabled": False,
    "extra_content": "",
    "extra_title":   "Additional notes",
    "layout":      "portrait",
    "margin_mm":   15,
    "show_page_numbers": True,
}


def _ensure_table():
    execute("""CREATE TABLE IF NOT EXISTS print_profiles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        config TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


def get_profile(name="default"):
    _ensure_table()
    if name not in CONTEXTS:
        name = "default"
    row = one("SELECT config FROM print_profiles WHERE name=?", (name,))
    out = dict(DEFAULT_PROFILE)
    if row:
        try:
            out.update(json.loads(row["config"]))
        except Exception:
            pass
    else:
        execute("INSERT OR IGNORE INTO print_profiles(name,config) VALUES(?,?)",
                (name, json.dumps(DEFAULT_PROFILE)))
    return out


def save_profile(name, config):
    _ensure_table()
    if name not in CONTEXTS:
        name = "default"
    payload = json.dumps(config)
    if one("SELECT id FROM print_profiles WHERE name=?", (name,)):
        execute("UPDATE print_profiles SET config=?, updated_at=CURRENT_TIMESTAMP "
                "WHERE name=?", (payload, name))
    else:
        execute("INSERT INTO print_profiles(name,config) VALUES(?,?)",
                (name, payload))


def list_profiles():
    _ensure_table()
    rows = query("SELECT name, updated_at FROM print_profiles ORDER BY name")
    have = {r["name"]: r["updated_at"] for r in rows}
    return [{"name": k, "label": CONTEXTS[k], "updated_at": have.get(k)}
            for k in CONTEXTS]
