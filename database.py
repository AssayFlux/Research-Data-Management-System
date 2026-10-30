"""
PAGEPATTERN — SQLite schema + helpers.

AUTHORITATIVE SCHEMA — must match data/research.db exactly.
Any schema change must be reflected here AND in a migration file.
"""
import sqlite3
import json
from pathlib import Path
from config import DB_PATH, DATA_DIR, DEFAULT_SETTINGS


# ═════════════════════════════════════════════════════════════
# SCHEMA VERSION
# ═════════════════════════════════════════════════════════════
SCHEMA_VERSION = 2


# ═════════════════════════════════════════════════════════════
# FULL SCHEMA — 34 tables
# ═════════════════════════════════════════════════════════════
SCHEMA = """
PRAGMA foreign_keys = ON;

-- ─────── version tracking ───────
CREATE TABLE IF NOT EXISTS schema_version(
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note       TEXT DEFAULT ''
);

-- ─────── users & auth ───────
CREATE TABLE IF NOT EXISTS users(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('ADMIN','RESEARCHER','VIEWER')),
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT,
    avatar_type   TEXT DEFAULT 'initials',
    avatar_value  TEXT DEFAULT '',
    avatar_style  TEXT DEFAULT '',
    totp_secret   TEXT DEFAULT '',
    totp_enabled  INTEGER DEFAULT 0,
    totp_backup_codes TEXT DEFAULT '',
    display_name  TEXT DEFAULT '',
    email         TEXT DEFAULT '',
    must_change_password INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS login_attempts(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT NOT NULL,
    ip           TEXT NOT NULL,
    success      INTEGER NOT NULL DEFAULT 0,
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_login_attempts
    ON login_attempts(username, ip, attempted_at);

CREATE TABLE IF NOT EXISTS user_sessions(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    token      TEXT UNIQUE NOT NULL,
    device     TEXT,
    ip         TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen  TEXT DEFAULT CURRENT_TIMESTAMP,
    revoked    INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS password_resets(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    token      TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    used       INTEGER DEFAULT 0,
    ip         TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS webauthn_credentials(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    credential_id TEXT UNIQUE NOT NULL,
    public_key    TEXT NOT NULL,
    sign_count    INTEGER DEFAULT 0,
    transports    TEXT DEFAULT '',
    name          TEXT DEFAULT 'Fingerprint',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_used     TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ─────── settings ───────
CREATE TABLE IF NOT EXISTS settings(
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS print_profiles(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT UNIQUE NOT NULL,
    config     TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ─────── studies ───────
CREATE TABLE IF NOT EXISTS studies(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    study_code    TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT DEFAULT '',
    pi            TEXT DEFAULT '',
    institution   TEXT DEFAULT '',
    department    TEXT DEFAULT '',
    protocol_no   TEXT DEFAULT '',
    ethics_no     TEXT DEFAULT '',
    start_date    TEXT,
    end_date      TEXT,
    status        TEXT DEFAULT 'ACTIVE',
    archived      INTEGER DEFAULT 0,
    sample_target INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    frozen        INTEGER DEFAULT 0,
    frozen_at     TEXT,
    frozen_by     INTEGER,
    freeze_reason TEXT DEFAULT '',
    cutoff_date   TEXT
);

CREATE TABLE IF NOT EXISTS study_users(
    study_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    PRIMARY KEY(study_id, user_id),
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id)  REFERENCES users(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS freeze_log(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id   INTEGER,
    action     TEXT NOT NULL,
    reason     TEXT DEFAULT '',
    user_id    INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id)  REFERENCES users(id)   ON DELETE SET NULL
);

-- ─────── participants ───────
CREATE TABLE IF NOT EXISTS participants(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id          INTEGER NOT NULL,
    participant_code  TEXT NOT NULL,
    consent_status    TEXT DEFAULT 'Pending',
    visit_date        TEXT,
    sex               TEXT,
    age               REAL,
    group_type        TEXT DEFAULT 'Unclassified',
    group_reason      TEXT DEFAULT '',
    screening_status  TEXT DEFAULT 'Screened',
    enrollment_status TEXT DEFAULT 'Enrolled',
    notes             TEXT DEFAULT '',
    archived          INTEGER DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    classification    TEXT DEFAULT 'Undetermined',
    classification_reason TEXT DEFAULT '',
    classified_at     TEXT,
    locked            INTEGER DEFAULT 0,
    UNIQUE(study_id, participant_code),
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_participants_study ON participants(study_id);
CREATE INDEX IF NOT EXISTS idx_participants_code  ON participants(participant_code);

CREATE TABLE IF NOT EXISTS visit_schedules(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    visit_number   INTEGER DEFAULT 1,
    visit_name     TEXT DEFAULT 'Visit',
    target_date    TEXT,
    actual_date    TEXT,
    status         TEXT DEFAULT 'Scheduled',
    notes          TEXT DEFAULT '',
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS biospecimens(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id  INTEGER NOT NULL,
    sample_id       TEXT NOT NULL,
    sample_type     TEXT,
    collection_date TEXT,
    storage_location TEXT,
    freeze_thaw     INTEGER DEFAULT 0,
    volume          TEXT,
    notes           TEXT DEFAULT '',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS participant_files(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    filename       TEXT NOT NULL,
    original_name  TEXT,
    mime           TEXT,
    size           INTEGER,
    uploaded_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

-- ─────── parameters ───────
CREATE TABLE IF NOT EXISTS parameter_groups(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT UNIQUE NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS parameters(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    group_id    INTEGER,
    category    TEXT DEFAULT 'Other',
    data_type   TEXT DEFAULT 'Decimal',
    unit        TEXT DEFAULT '',
    description TEXT DEFAULT '',
    ref_low     REAL,
    ref_high    REAL,
    ref_text    TEXT DEFAULT '',
    choices     TEXT DEFAULT '',
    min_value   REAL,
    max_value   REAL,
    required    INTEGER DEFAULT 0,
    sort_order  INTEGER DEFAULT 0,
    formula     TEXT DEFAULT '',
    active      INTEGER DEFAULT 1,
    FOREIGN KEY(group_id) REFERENCES parameter_groups(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_parameters_code ON parameters(code);

-- ─────── forms ───────
CREATE TABLE IF NOT EXISTS forms(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id    INTEGER,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    status      TEXT DEFAULT 'DRAFT',
    version     INTEGER DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(study_id) REFERENCES studies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS form_fields(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id           INTEGER NOT NULL,
    parameter_id      INTEGER NOT NULL,
    section           TEXT DEFAULT 'General',
    display_order     INTEGER DEFAULT 0,
    required_override INTEGER,
    FOREIGN KEY(form_id)      REFERENCES forms(id)      ON DELETE CASCADE,
    FOREIGN KEY(parameter_id) REFERENCES parameters(id) ON DELETE CASCADE
);

-- ─────── records & values ───────
CREATE TABLE IF NOT EXISTS participant_records(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    form_id        INTEGER,
    visit_date     TEXT,
    created_by     INTEGER,
    locked         INTEGER DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lock_reason    TEXT DEFAULT '',
    locked_by      INTEGER,
    locked_at      TEXT,
    edit_count     INTEGER DEFAULT 0,
    last_edited_by INTEGER,
    last_edited_at TEXT,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    FOREIGN KEY(form_id)        REFERENCES forms(id)        ON DELETE SET NULL,
    FOREIGN KEY(created_by)     REFERENCES users(id)        ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_records_participant ON participant_records(participant_id);

CREATE TABLE IF NOT EXISTS participant_values(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     INTEGER NOT NULL,
    parameter_id  INTEGER NOT NULL,
    value_text    TEXT,
    numeric_value REAL,
    value_state   TEXT DEFAULT 'VALUE'
                  CHECK(value_state IN ('VALUE','MISSING','NOT_APPLICABLE','UNKNOWN')),
    FOREIGN KEY(record_id)    REFERENCES participant_records(id) ON DELETE CASCADE,
    FOREIGN KEY(parameter_id) REFERENCES parameters(id)          ON DELETE CASCADE,
    UNIQUE(record_id, parameter_id)
);
CREATE INDEX IF NOT EXISTS idx_values_record    ON participant_values(record_id);
CREATE INDEX IF NOT EXISTS idx_values_parameter ON participant_values(parameter_id);

CREATE TABLE IF NOT EXISTS record_edits(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id     INTEGER NOT NULL,
    user_id       INTEGER,
    action        TEXT NOT NULL,
    field_changes TEXT DEFAULT '',
    notes         TEXT DEFAULT '',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(record_id) REFERENCES participant_records(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id)   REFERENCES users(id)               ON DELETE SET NULL
);

-- ─────── formulas ───────
CREATE TABLE IF NOT EXISTS formulas(
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    code                TEXT UNIQUE NOT NULL,
    expression          TEXT NOT NULL,
    description         TEXT DEFAULT '',
    output_parameter_id INTEGER,
    active              INTEGER DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(output_parameter_id) REFERENCES parameters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS formula_inputs(
    formula_id   INTEGER NOT NULL,
    parameter_id INTEGER NOT NULL,
    PRIMARY KEY(formula_id, parameter_id),
    FOREIGN KEY(formula_id)   REFERENCES formulas(id)   ON DELETE CASCADE,
    FOREIGN KEY(parameter_id) REFERENCES parameters(id) ON DELETE CASCADE
);

-- ─────── criteria ───────
CREATE TABLE IF NOT EXISTS criteria(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    study_id     INTEGER,
    kind         TEXT NOT NULL CHECK(kind IN ('inclusion','exclusion','control','study')),
    name         TEXT NOT NULL,
    parameter_id INTEGER,
    operator     TEXT NOT NULL,
    value1       TEXT,
    value2       TEXT,
    logic_group  TEXT DEFAULT 'default',
    active       INTEGER DEFAULT 1,
    description  TEXT DEFAULT '',
    sort_order   INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(study_id)     REFERENCES studies(id)    ON DELETE CASCADE,
    FOREIGN KEY(parameter_id) REFERENCES parameters(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS participant_criteria_results(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    criteria_id    INTEGER NOT NULL,
    passed         INTEGER,
    message        TEXT DEFAULT '',
    evaluated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    FOREIGN KEY(criteria_id)    REFERENCES criteria(id)     ON DELETE CASCADE
);

-- ─────── alerts & quality ───────
CREATE TABLE IF NOT EXISTS critical_rules(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    parameter_id INTEGER NOT NULL,
    operator     TEXT NOT NULL,
    value1       REAL,
    value2       REAL,
    severity     TEXT DEFAULT 'warning',
    message      TEXT,
    active       INTEGER DEFAULT 1,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(parameter_id) REFERENCES parameters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER,
    parameter_id   INTEGER,
    record_id      INTEGER,
    rule_id        INTEGER,
    severity       TEXT,
    message        TEXT,
    acknowledged   INTEGER DEFAULT 0,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    FOREIGN KEY(parameter_id)   REFERENCES parameters(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quality_checks(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER,
    parameter_id   INTEGER,
    severity       TEXT,
    message        TEXT,
    resolved       INTEGER DEFAULT 0,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    FOREIGN KEY(parameter_id)   REFERENCES parameters(id)   ON DELETE CASCADE
);

-- ─────── inter-rater ───────
CREATE TABLE IF NOT EXISTS inter_rater_entries(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER NOT NULL,
    parameter_id   INTEGER NOT NULL,
    rater1_user    INTEGER,
    rater1_value   TEXT,
    rater2_user    INTEGER,
    rater2_value   TEXT,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    FOREIGN KEY(parameter_id)   REFERENCES parameters(id)   ON DELETE CASCADE
);

-- ─────── adverse events ───────
CREATE TABLE IF NOT EXISTS adverse_events(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    participant_id INTEGER,
    event_date     TEXT,
    term           TEXT,
    severity       TEXT,
    outcome        TEXT,
    notes          TEXT DEFAULT '',
    resolved       INTEGER DEFAULT 0,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
    causality      TEXT DEFAULT 'Not assessed',
    action_taken   TEXT DEFAULT '',
    expected       TEXT DEFAULT '',
    serious        INTEGER DEFAULT 0,
    expectedness   TEXT DEFAULT '',
    resolved_date  TEXT,
    FOREIGN KEY(participant_id) REFERENCES participants(id) ON DELETE CASCADE
);

-- ─────── email ───────
CREATE TABLE IF NOT EXISTS email_queue(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient  TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT,
    status     TEXT DEFAULT 'pending',
    error      TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    sent_at    TEXT
);

-- ─────── saved queries ───────
CREATE TABLE IF NOT EXISTS saved_queries(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    study_id   INTEGER,
    definition TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(study_id)   REFERENCES studies(id) ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES users(id)   ON DELETE SET NULL
);

-- ─────── audit log ───────
CREATE TABLE IF NOT EXISTS audit_log(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    action      TEXT NOT NULL,
    target_type TEXT DEFAULT '',
    target_id   TEXT DEFAULT '',
    details     TEXT DEFAULT '',
    ip          TEXT DEFAULT '',
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit_log(user_id);
"""


# ═════════════════════════════════════════════════════════════
# CONNECTION
# ═════════════════════════════════════════════════════════════
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=30000")
    return c


# ═════════════════════════════════════════════════════════════
# INITIALIZE
# ═════════════════════════════════════════════════════════════
def init_db():
    c = connect()
    try:
        c.executescript(SCHEMA)
        # Record version
        cur = c.execute("SELECT MAX(version) v FROM schema_version").fetchone()
        current = cur["v"] if cur and cur["v"] else 0
        if current < SCHEMA_VERSION:
            c.execute(
                "INSERT OR REPLACE INTO schema_version(version, note) VALUES(?,?)",
                (SCHEMA_VERSION, "auto-applied from database.py")
            )
        # Default settings
        for k, v in DEFAULT_SETTINGS.items():
            c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    finally:
        c.close()
    # Apply any pending migrations
    migrate_db()


def get_schema_version():
    c = connect()
    try:
        cur = c.execute("SELECT MAX(version) v FROM schema_version").fetchone()
        return cur["v"] if cur and cur["v"] else 0
    except Exception:
        return 0
    finally:
        c.close()


# ═════════════════════════════════════════════════════════════
# QUERY HELPERS
# ═════════════════════════════════════════════════════════════
def query(sql, args=()):
    c = connect()
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def one(sql, args=()):
    c = connect()
    try:
        return c.execute(sql, args).fetchone()
    finally:
        c.close()


def execute(sql, args=()):
    c = connect()
    try:
        return c.execute(sql, args).lastrowid
    finally:
        c.close()


def settings_dict():
    return {r["key"]: r["value"] for r in query("SELECT key,value FROM settings")}


def setting(key, default=""):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else default


def set_setting(key, value):
    execute("INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)))


def json_load(s, default=None):
    try:
        return json.loads(s) if s else default
    except Exception:
        return default

# ═════════════════════════════════════════════════════════════
# SESSION HELPERS
# ═════════════════════════════════════════════════════════════
def revoke_user_sessions(user_id, except_token=None):
    """Revoke all sessions for a user, optionally keeping one token alive.
    Returns number of sessions revoked."""
    c = connect()
    try:
        if except_token:
            cur = c.execute(
                "UPDATE user_sessions SET revoked=1 "
                "WHERE user_id=? AND token!=? AND revoked=0",
                (user_id, except_token))
        else:
            cur = c.execute(
                "UPDATE user_sessions SET revoked=1 "
                "WHERE user_id=? AND revoked=0",
                (user_id,))
        return cur.rowcount or 0
    finally:
        c.close()

# ═════════════════════════════════════════════════════════════
# MIGRATIONS — safe for existing databases
# ═════════════════════════════════════════════════════════════
def migrate_db():
    """Apply incremental schema changes to existing databases."""
    c = connect()
    try:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(users)").fetchall()]
        if "must_change_password" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
            print("[migration] users.must_change_password added")
    finally:
        c.close()

# ═════════════════════════════════════════════════════════════
# STUDY-LEVEL PERMISSIONS
# ═════════════════════════════════════════════════════════════
def visible_study_ids(user):
    """Return None (unrestricted) or a set of study IDs the user may see.

    Rules:
      ADMIN       → None (all studies)
      RESEARCHER/VIEWER with assignments → only those study IDs
      RESEARCHER/VIEWER with zero assignments → None (legacy unrestricted)
        — this preserves existing installs where study_users was never populated.
        To enforce strict mode, populate study_users for every non-admin user.
    """
    if not user:
        return set()
    try:
        from flask import g
        cached = getattr(g, "_visible_study_ids", "__none__")
        if cached != "__none__":
            return cached
    except Exception:
        g = None

    role = user["role"] if "role" in user.keys() else ""
    if role == "ADMIN":
        result = None
    else:
        assigned = [r["study_id"] for r in query(
            "SELECT study_id FROM study_users WHERE user_id=?",
            (user["id"],))]
        # Legacy behaviour: no assignments = unrestricted
        result = set(assigned) if assigned else None

    try:
        from flask import g
        g._visible_study_ids = result
    except Exception:
        pass
    return result


def can_access_study(user, study_id):
    """True if the user is allowed to see the given study."""
    if not user:
        return False
    if user["role"] == "ADMIN":
        return True
    visible = visible_study_ids(user)
    if visible is None:
        return True
    try:
        return int(study_id) in visible
    except (TypeError, ValueError):
        return False
