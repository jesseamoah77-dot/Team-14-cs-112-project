"""
Clinic-wide announcements: publish/expiry dates, urgent or routine, auto-archived.

Another storage gap in the brief's file list (like appointments) - the feature is
specified in detail but has no home among the five listed JSON files. Announcements
are clinic-scoped: patients only see their own clinic's notices.
"""

from datetime import date, datetime

from models import store
from utils.validators import ValidationError, require


def create(clinic_id, title, body, publish_date=None, expiry_date=None, urgent=False):
    title = require(title, "Title")
    body = require(body, "Announcement text")
    publish = _parse(publish_date) if publish_date else date.today().isoformat()
    expiry = _parse(expiry_date) if expiry_date else None
    if expiry and expiry < publish:
        raise ValidationError("Expiry date is before the publish date.")

    def _apply(data):
        announcement_id = store.next_id("announcements", "N")
        data[announcement_id] = {
            "clinic_id": clinic_id, "title": title, "body": body,
            "publish_date": publish, "expiry_date": expiry, "urgent": bool(urgent),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return announcement_id
    return store.update("announcements", _apply)


def _parse(value):
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid date - use YYYY-MM-DD.")


def active_for_clinic(clinic_id, today=None):
    """Published and not expired, urgent ones first."""
    today = today or date.today().isoformat()
    out = []
    for announcement_id, a in store.load("announcements").items():
        if a["clinic_id"] != clinic_id:
            continue
        if a["publish_date"] > today:
            continue
        if a["expiry_date"] and a["expiry_date"] < today:
            continue  # expired -> archived automatically by falling out of this view
        out.append({"id": announcement_id, **a})
    return sorted(out, key=lambda a: (not a["urgent"], a["publish_date"]), reverse=False)


def all_for_clinic(clinic_id):
    """Including expired - the clinician's archive view."""
    out = [{"id": aid, **a} for aid, a in store.load("announcements").items()
           if a["clinic_id"] == clinic_id]
    return sorted(out, key=lambda a: a["publish_date"], reverse=True)
