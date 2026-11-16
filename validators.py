"""Small input validation helpers. Every function raises ValueError with a clear message."""
import math
from datetime import date


def to_number(value, name, low, high, default=None):
    """Return value as a float between low and high (or default when missing)."""
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError("%s is required" % name)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number" % name)
    if not math.isfinite(number) or not (low <= number <= high):
        raise ValueError("%s must be between %g and %g" % (name, low, high))
    return number


def to_date(value, name="date", default=None):
    """Return an ISO date string (YYYY-MM-DD)."""
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError("%s is required" % name)
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise ValueError("%s must be YYYY-MM-DD" % name)


def to_choice(value, options, name, default=None):
    if value is None or value == "":
        if default is not None:
            return default
        raise ValueError("%s is required" % name)
    value = str(value).strip().lower()
    if value not in options:
        raise ValueError("%s must be one of: %s" % (name, ", ".join(options)))
    return value


def to_text(value, name, max_len=60, required=True):
    text = "" if value is None else str(value).strip()
    if not text:
        if required:
            raise ValueError("%s is required" % name)
        return ""
    if len(text) > max_len:
        raise ValueError("%s is too long (max %d characters)" % (name, max_len))
    return text
