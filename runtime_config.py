"""Runtime configuration — DB settings override config.py defaults.

Every module that needs session hours, remember days, login limits,
or branding MUST read from here, not from config.py directly.
"""
from database import settings_dict


def _int(d, key, default):
    try:
        return int(d.get(key, default))
    except (TypeError, ValueError):
        return default


def _bool(d, key, default=False):
    v = str(d.get(key, default)).strip().lower()
    return v in ("1", "true", "yes", "on")


def get_runtime():
    """Return a dict of effective runtime settings (DB > config.py)."""
    from config import (SESSION_HOURS, REMEMBER_DAYS,
                        LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_MINUTES)
    s = settings_dict()
    return {
        # security
        "session_hours":        _int(s, "session_hours", SESSION_HOURS),
        "remember_days":        _int(s, "remember_days", REMEMBER_DAYS),
        "login_max_attempts":   _int(s, "login_max_attempts", LOGIN_MAX_ATTEMPTS),
        "login_window_minutes": _int(s, "login_window_minutes", LOGIN_WINDOW_MINUTES),
        # login page
        "login_title":          s.get("login_title", "Sign in"),
        "login_subtitle":       s.get("login_subtitle", ""),
        "login_bg":             s.get("login_bg", ""),
        "allow_remember":       _bool(s, "allow_remember", True),
        # branding
        "brand_mark_type":      s.get("brand_mark_type", "emoji"),
        "brand_mark_value":     s.get("brand_mark_value", "✚"),
        "brand_logo_url":       s.get("brand_logo_url", ""),
        "favicon_url":          s.get("favicon_url", ""),
        "login_logo_url":       s.get("login_logo_url", ""),
        "login_bg_type":        s.get("login_bg_type", "color"),
        "login_bg_value":       s.get("login_bg_value", "#f7f9fb"),
        # appearance
        "ui_primary":           s.get("ui_primary", ""),
        "ui_accent":            s.get("ui_accent", ""),
        "ui_page_bg":           s.get("ui_page_bg", ""),
        "ui_sidebar_w":         s.get("ui_sidebar_w", ""),
        "ui_font_size":         s.get("ui_font_size", ""),
        "ui_compact":           _bool(s, "ui_compact", False),
    }
