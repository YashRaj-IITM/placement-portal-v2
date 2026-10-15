import re
from datetime import datetime, timezone

from flask import jsonify, request
from flask_security import auth_required, roles_required

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Raised for bad client input; converted to a 400 JSON response."""


def error(message, status=400):
    return jsonify({"message": message}), status


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")
    return data


def token_roles(*roles):
    """Require a valid access token AND one of the given roles."""

    def decorator(fn):
        return auth_required("token")(roles_required(*roles)(fn))

    return decorator


def text(value, label, min_len=0, max_len=255, required=False):
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ValidationError(f"{label} is required")
    if value and len(value) < min_len:
        raise ValidationError(f"{label} must be at least {min_len} characters")
    if len(value) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters")
    return value


def number(value, label, cast=float, lo=None, hi=None):
    """Parse an optional number. None / '' -> None."""
    if value is None or value == "":
        return None
    try:
        value = cast(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{label} must be a valid number")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        raise ValidationError(f"{label} must be between {lo} and {hi}")
    return value


def csv_list(value, label):
    """Accept 'CSE, ECE' or ['CSE','ECE'] and return 'CSE,ECE'."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        items = [str(v).strip() for v in value]
    elif isinstance(value, str):
        items = [v.strip() for v in value.split(",")]
    else:
        raise ValidationError(f"{label} must be a comma separated string")
    return ",".join(i for i in items if i)


def parse_datetime(value, label="Date"):
    """Parse ISO 8601 into a naive UTC datetime."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} is required")
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(f"{label} must be an ISO 8601 date-time")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def search_like(q):
    return f"%{q.strip()}%" if q and q.strip() else None
