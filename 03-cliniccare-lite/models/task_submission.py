"""
Patient submissions and the clinician review workflow.

Review outcomes are categorical - Pending / Reviewed - Normal / Needs Follow-up /
Escalated - never a numeric score. The brief is explicit about why: these are
health-related records, and a 0-100 grade is the wrong frame entirely. The outcome
records who reviewed, when, the outcome, free-text notes, and whether the patient
was notified.

Keyed "patientID_taskID", which also makes "one submission per patient per task" a
property of the storage itself; resubmission before review overwrites (documented
behaviour, tested).
"""

from datetime import datetime

from models import health_task, store
from utils.validators import ValidationError

REVIEW_OUTCOMES = ("Pending", "Reviewed - Normal", "Needs Follow-up", "Escalated")


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def record(patient_id, task_id, file_path, completeness):
    """Store/replace the submission record after the file is already safely saved."""
    task = health_task.get(task_id)
    if task is None:
        raise ValidationError(f"Task {task_id} does not exist.")
    if patient_id not in task["assigned_patient_ids"]:
        raise ValidationError("That task is not assigned to you.")

    key = f"{patient_id}_{task_id}"

    def _apply(data):
        previous = data.get(key)
        if previous and previous["review"]["outcome"] != "Pending":
            raise ValidationError(
                "This submission has already been reviewed - contact your clinician "
                "if it needs to be replaced.")
        data[key] = {
            "patient_id": patient_id,
            "task_id": task_id,
            "file_path": file_path,
            "submitted_at": _now(),
            "resubmission": previous is not None,
            "completeness": completeness,
            "review": {"outcome": "Pending", "reviewer_id": None, "reviewed_at": None,
                       "notes": None, "patient_notified": False},
        }
        return key
    return store.update("task_submissions", _apply)


def review(key, reviewer_id, outcome, notes=""):
    if outcome not in REVIEW_OUTCOMES or outcome == "Pending":
        valid = ", ".join(o for o in REVIEW_OUTCOMES if o != "Pending")
        raise ValidationError(f"Outcome must be one of: {valid}.")

    def _apply(data):
        if key not in data:
            raise ValidationError("Submission not found.")
        data[key]["review"] = {
            "outcome": outcome, "reviewer_id": reviewer_id, "reviewed_at": _now(),
            "notes": (notes or "").strip() or None, "patient_notified": False,
        }
    store.update("task_submissions", _apply)


def mark_notified(key):
    def _apply(data):
        if key in data:
            data[key]["review"]["patient_notified"] = True
    store.update("task_submissions", _apply)


def get(key):
    return store.load("task_submissions").get(key)


def for_patient(patient_id):
    return {k: s for k, s in store.load("task_submissions").items()
            if s["patient_id"] == patient_id}


def for_clinic(clinic_id, task_id=None, patient_id=None, outcome=None):
    """Clinician dashboard listing with the spec's filters (task, patient, status)."""
    clinic_tasks = set(health_task.for_clinic(clinic_id))
    out = {}
    for key, sub in store.load("task_submissions").items():
        if sub["task_id"] not in clinic_tasks:
            continue
        if task_id and sub["task_id"] != task_id:
            continue
        if patient_id and sub["patient_id"] != patient_id:
            continue
        if outcome and sub["review"]["outcome"] != outcome:
            continue
        out[key] = sub
    return out
