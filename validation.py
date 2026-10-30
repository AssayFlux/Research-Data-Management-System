"""PAGEPATTERN — input validation returning (text, numeric, state, error)."""
from datetime import datetime

NUMERIC = {"Integer", "Decimal"}
STATE_TOKENS = {
    "__MISSING__":       "MISSING",
    "__NOT_APPLICABLE__":"NOT_APPLICABLE",
    "__UNKNOWN__":       "UNKNOWN",
}

def validate_value(param, raw):
    """Return (value_text, numeric_value, value_state, error_msg_or_None)."""
    raw = "" if raw is None else str(raw).strip()

    # Non-value states
    if raw in STATE_TOKENS:
        return None, None, STATE_TOKENS[raw], None

    if param["required"] and not raw:
        return None, None, "MISSING", "This field is required."

    if not raw:
        return None, None, "MISSING", None

    dtype = param["data_type"]

    if dtype in NUMERIC:
        try:
            val = int(raw) if dtype == "Integer" else float(raw)
        except ValueError:
            return None, None, "VALUE", "Enter a valid numeric value."
        lo, hi = param["min_value"], param["max_value"]
        if lo is not None and val < lo:
            return None, None, "VALUE", f"Value must be \u2265 {lo}."
        if hi is not None and val > hi:
            return None, None, "VALUE", f"Value must be \u2264 {hi}."
        return None, float(val), "VALUE", None

    if dtype == "Date":
        try:
            datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            return None, None, "VALUE", "Use YYYY-MM-DD format."
        return raw, None, "VALUE", None

    if dtype in ("Choice", "Multiple choice"):
        choices = [c.strip() for c in (param["choices"] or "").split(",") if c.strip()]
        if choices and raw not in choices:
            return None, None, "VALUE", "Select a valid choice."
        return raw, None, "VALUE", None

    if dtype in ("Yes/No", "Boolean"):
        if raw.lower() not in ("yes", "no", "true", "false", "1", "0"):
            return None, None, "VALUE", "Enter Yes or No."
        return raw, None, "VALUE", None

    return raw, None, "VALUE", None
