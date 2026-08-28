"""
Send 24-hour appointment reminders.

    python send_reminders.py

Meant to be run on a schedule (Task Scheduler / cron, hourly is plenty); running it
by hand does the same thing and is how the demo shows the feature. Each reminder
goes to the patient's inbox and email, and the appointment is marked so it is never
reminded twice.
"""

from models import appointment, message, user
from utils import email_handler


def main():
    due = appointment.due_for_reminder(within_hours=24)
    if not due:
        print("No reminders due.")
        return
    for appointment_id, record in due.items():
        patient = user.get(record["patient_id"])
        if patient is None:
            continue
        text = (f"Reminder: you have an appointment on {record['when']} - "
                f"{record['purpose']}.")
        message.notify(patient.user_id, text)
        email_handler.send_email(patient.email, "Appointment reminder",
                                 f"Hello {patient.name},\n\n{text}\n")
        appointment.mark_reminder_sent(appointment_id)
        print(f"Reminded {patient.user_id} about {appointment_id} ({record['when']})")


if __name__ == "__main__":
    main()
