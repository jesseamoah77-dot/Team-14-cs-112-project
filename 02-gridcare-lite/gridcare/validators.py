"""Input validation helpers shared by the services layer and the GUI forms."""

from datetime import date, datetime

from .services import ValidationError


def parse_date(value, allow_past=True):
    """
    Accept a YYYY-MM-DD string, return it normalised, or raise ValidationError.

    strptime rejects impossible dates (2026-02-31, month 13) as well as wrong formats,
    which covers the brief's "invalid dates" test cases in one place.
    """
    value = (value or "").strip()
    if not value:
        raise ValidationError("Date is required (format YYYY-MM-DD).")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid date - use YYYY-MM-DD.")
    if not allow_past and parsed < date.today():
        raise ValidationError(f"{parsed} is in the past - scheduled dates must be today or later.")
    return parsed.isoformat()


def require_fields(**fields):
    """require_fields(Description=desc, Severity=sev) -> ValidationError naming the first blank."""
    for label, value in fields.items():
        if value is None or not str(value).strip():
            raise ValidationError(f"{label} is required.")
