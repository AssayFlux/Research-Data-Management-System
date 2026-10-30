"""PAGEPATTERN — global configuration."""
import os, secrets
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent
DATA_DIR      = BASE_DIR / "data"
BACKUP_DIR    = BASE_DIR / "backups"
CONTENT_DIR   = BASE_DIR / "content"
LEARN_DIR     = CONTENT_DIR / "learn"
BRANDING_DIR  = BASE_DIR / "branding"
UPLOAD_DIR    = DATA_DIR / "uploads"
STATIC_DIR    = BASE_DIR / "static"
DB_PATH       = DATA_DIR / "research.db"
SECRET_FILE   = DATA_DIR / ".secret_key"

for _p in (DATA_DIR, BACKUP_DIR, CONTENT_DIR, LEARN_DIR, BRANDING_DIR,
           UPLOAD_DIR, UPLOAD_DIR / "prescriptions"):
    _p.mkdir(parents=True, exist_ok=True)

if SECRET_FILE.exists():
    SECRET_KEY = SECRET_FILE.read_text().strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    SECRET_FILE.write_text(SECRET_KEY)
    try: SECRET_FILE.chmod(0o600)
    except Exception: pass
SECRET_KEY = os.environ.get("RDM_SECRET_KEY", SECRET_KEY)

APP_NAME    = "Research Data Management System"
APP_TAGLINE = "Clinical research workspace"
SESSION_HOURS = 12
REMEMBER_DAYS = 30
MAX_CONTENT_LENGTH = 32 * 1024 * 1024
ROLES = ("ADMIN","RESEARCHER","VIEWER")
LOGIN_MAX_ATTEMPTS   = 5
LOGIN_WINDOW_MINUTES = 15
DATA_TYPES = ("Integer","Decimal","Choice","Date","Yes/No","Boolean","Long text","Text")
VALUE_STATES = ("VALUE","MISSING","NOT_APPLICABLE","UNKNOWN")
CONSENT_STATES = ("Pending","Obtained","Declined")
SCREENING_STATES = ("Screened","Eligible","Ineligible")
ENROLLMENT_STATES = ("Enrolled","Withdrawn","Completed")
DEFAULT_GROUPS = ("Case","Control","Treatment","Placebo","Unclassified")
ALLOWED_IMAGE_EXTS = {".png",".jpg",".jpeg",".gif",".webp",".svg",".ico"}

PALETTE = {
    "primary":"#0f766e","primary_hover":"#115e59","accent":"#14b8a6",
    "page_bg":"#f7f9fb","card":"#ffffff","surface_alt":"#fafbfc",
    "hover":"#f1f5f9","border":"#e5e9ef",
    "text_dark":"#0f172a","text_body":"#334155","text_muted":"#64748b",
    "success":"#059669","success_bg":"#ecfdf5",
    "warning":"#d97706","warning_bg":"#fffbeb",
    "danger":"#dc2626","danger_bg":"#fef2f2",
    "info":"#2563eb","info_bg":"#eff6ff",
}

DEFAULT_SETTINGS = {
    "app_name":APP_NAME,"app_tagline":APP_TAGLINE,"institution":"",
    "department":"","copyright":"© PAGEPATTERN",
    "session_hours":str(SESSION_HOURS),"remember_days":str(REMEMBER_DAYS),
    "auto_backup":"0","backup_keep":"10",
}
