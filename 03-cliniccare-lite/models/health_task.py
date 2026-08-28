"""
Health tasks: administrative assignments from a clinician to patients.

"Submit your home blood-pressure log by Friday" - a title, instructions, a due date,
which patients it's assigned to, and optionally the field names the automated
completeness check should look for in a .csv/.txt submission (structure only - the
checker never reads meaning into the values; that boundary is enforced in
utils/completeness.py).
"""

from datetime import date, datetime

from models import store
from utils.validators import ValidationError, require


def create(clinic_id, title, description, due_date, assigned_patient_ids,
           expected_fields=None):
    title = require(title, "Title")
    description = require(description, "Instructions")
    due = _parse_due(due_date)
    if not assigned_patient_ids:
        raise ValidationError("Assign the task to at least one patient.")

    def _apply(data):
        task_id = store.next_id("health_tasks", "T")
        data[task_id] = {
            "clinic_id": clinic_id,
            "title": title,
            "description": description,
            "due_date": due,
            "assigned_patient_ids": list(assigned_patient_ids),
            "expected_fields": [f.strip() for f in (expected_fields or []) if f.strip()],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return task_id
    return store.update("health_tasks", _apply)


def _parse_due(value):
    value = (value or "").strip()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"'{value}' is not a valid due date - use YYYY-MM-DD.")
    if parsed < date.today():
        raise ValidationError("Due date cannot be in the past.")
    return parsed.isoformat()


def get(task_id):
    return store.load("health_tasks").get(task_id)


def for_clinic(clinic_id):
    return {tid: t for tid, t in store.load("health_tasks").items()
            if t["clinic_id"] == clinic_id}


def for_patient(patient_id):
    return {tid: t for tid, t in store.load("health_tasks").items()
            if patient_id in t["assigned_patient_ids"]}


def is_assigned(task_id, patient_id):
    task = get(task_id)
    return bool(task) and patient_id in task["assigned_patient_ids"]
