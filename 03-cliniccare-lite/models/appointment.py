"""
Appointments - a storage file the brief's data-management section forgot.

The spec requires appointment reminders, a no-show analytics metric and patient
dashboard visibility, but its list of JSON files has nowhere to keep an appointment.
appointments.json fills that gap (documented in section 2 of the technical report).

Attendance status drives both the no-show analytics and the engagement tracker, and
is set by the clinician after the fact.
"""

from datetime import datetime

from models import store
from utils.validators import ValidationError, require

STATUSES = ("Scheduled", "Attended", "No-show", "Cancelled")


def create(clinic_id, patient_id, when, purpose):
    patient_id = require(patient_id, "Patient ID")
    purpose = require(purpose, "Purpose")

    try:
        parsed = datetime.strptime(
            (when or "").strip(),
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        raise ValidationError(
            "Appointment time must be YYYY-MM-DD HH:MM."
        )

    if parsed < datetime.now():
        raise ValidationError(
            "Appointment time is in the past."
        )

    def _apply(data):
        appointment_id = store.next_id(
            "appointments",
            "A"
        )

        data[appointment_id] = {
            "clinic_id": clinic_id,
            "patient_id": patient_id,
            "when": parsed.strftime("%Y-%m-%d %H:%M"),
            "purpose": purpose,
            "status": "Scheduled",
            "reminder_sent": False,
        }

        return appointment_id

    return store.update(
        "appointments",
        _apply
    )


def set_status(appointment_id, status, clinic_id=None, user_role="clinician"):
    if user_role != "clinician":
        raise ValidationError(
            "Only clinicians can change appointment status."
        )

    if status not in STATUSES:
        raise ValidationError(
            f"Status must be one of: {', '.join(STATUSES)}."
        )

    def _apply(data):
        appointment = data.get(appointment_id)

        if appointment is None:
            raise ValidationError(
                "Appointment not found."
            )

        if clinic_id is not None and appointment["clinic_id"] != clinic_id:
            raise ValidationError(
                "You cannot modify an appointment outside your clinic."
            )

        if appointment["status"] == "Attended" and status != "Attended":
            raise ValidationError(
                "An attended appointment cannot be changed."
            )

        if appointment["status"] == "No-show" and status != "No-show":
            raise ValidationError(
                "A no-show appointment cannot be changed."
            )

        if appointment["status"] == "Cancelled" and status != "Cancelled":
            raise ValidationError(
                "A cancelled appointment cannot be changed."
            )

        appointment["status"] = status

        if status != "Scheduled":
            appointment["reminder_sent"] = True

    store.update(
        "appointments",
        _apply
    )


def mark_reminder_sent(appointment_id):
    def _apply(data):
        if appointment_id in data:
            data[appointment_id]["reminder_sent"] = True

    store.update(
        "appointments",
        _apply
    )


def for_patient(patient_id):
    return {
        aid: appointment
        for aid, appointment in store.load("appointments").items()
        if appointment["patient_id"] == patient_id
    }


def for_clinic(clinic_id):
    return {
        aid: appointment
        for aid, appointment in store.load("appointments").items()
        if appointment["clinic_id"] == clinic_id
    }


def due_for_reminder(within_hours=24):
    now = datetime.now()
    out = {}

    for aid, appointment in store.load("appointments").items():
        if appointment["status"] != "Scheduled":
            continue

        if appointment["reminder_sent"]:
            continue

        when = datetime.strptime(
            appointment["when"],
            "%Y-%m-%d %H:%M"
        )

        hours = (
            when - now
        ).total_seconds() / 3600

        if 0 <= hours <= within_hours:
            out[aid] = appointment

    return out
