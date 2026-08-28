"""
Demo data for ClinicCare-Lite.

    python seed_demo.py

Accounts (ID / password):

    12350000 / Cl1nic!pass   clinician - Dr Akosua Sarpong, Adabraka Family Clinic
    11112024 / Pat1ent!aa    patient   - Kojo Mensah
    22222025 / Pat1ent!bb    patient   - Abena Osei
    33332026 / Pat1ent!cc    patient   - Yaw Owusu

Coursework demo credentials only. Seeds two tasks, one reviewed submission and one
awaiting review, a message thread, an urgent announcement, and three appointments
(one attended, one no-show, one upcoming) so every screen and every analytics
number has something to show.
"""

from datetime import datetime, timedelta
from pathlib import Path

import config
from models import (announcement, appointment, clinic, health_task, message, store,
                    task_submission, user)
from utils import engagement


def main():
    if store.load("users"):
        print("Users already exist - not seeding twice.")
        return 1

    doc = user.register("12350000", "Akosua Sarpong", "doc@example.com",
                        "Cl1nic!pass", "clinician")
    clinic_id = clinic.create("Adabraka Family Clinic", doc.user_id)
    doc.clinic_id = clinic_id
    doc.save()

    patients = [
        ("11112024", "Kojo Mensah", "Pat1ent!aa"),
        ("22222025", "Abena Osei", "Pat1ent!bb"),
        ("33332026", "Yaw Owusu", "Pat1ent!cc"),
    ]
    for pid, name, password in patients:
        p = user.register(pid, name, f"{pid}@example.com", password, "patient",
                          clinic_id=clinic_id)
        clinic.add_patient(clinic_id, pid)

    week_away = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    task_bp = health_task.create(
        clinic_id, "Weekly blood-pressure log",
        "Record your morning readings each day and submit them as a CSV with the "
        "columns Date and Systolic.", week_away,
        ["11112024", "22222025"], expected_fields=["Date", "Systolic"])
    task_intake = health_task.create(
        clinic_id, "Updated contact details form",
        "Download the intake form, fill in your current contact details and upload "
        "it as a PDF or text file.", week_away, ["11112024", "22222025", "33332026"])

    # Kojo already submitted the BP log and it has been reviewed.
    submissions_dir = Path(config.SUBMISSIONS_DIR) / clinic_id / "11112024"
    submissions_dir.mkdir(parents=True, exist_ok=True)
    csv_path = submissions_dir / f"11112024_{task_bp}.csv"
    csv_path.write_text("Date,Systolic\n2026-07-21,124\n2026-07-22,121\n2026-07-23,126\n",
                        encoding="utf-8")
    key = task_submission.record(
        "11112024", task_bp, csv_path.relative_to(config.SUBMISSIONS_DIR).as_posix(),
        {"complete": True, "checked_fields": ["Date", "Systolic"], "problems": []})
    task_submission.review(key, doc.user_id, "Reviewed - Normal",
                           "All readings recorded - thank you, keep the same schedule.")
    task_submission.mark_notified(key)
    engagement.on_submission("11112024", week_away,
                             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    message.notify("11112024",
                   "Submission reviewed - Reviewed - Normal: Weekly blood-pressure log")

    # Abena submitted the contact form and is waiting for review.
    abena_dir = Path(config.SUBMISSIONS_DIR) / clinic_id / "22222025"
    abena_dir.mkdir(parents=True, exist_ok=True)
    txt_path = abena_dir / f"22222025_{task_intake}.txt"
    txt_path.write_text("Name: Abena Osei\nPhone: 024-555-0123\nAddress: Adabraka\n",
                        encoding="utf-8")
    task_submission.record(
        "22222025", task_intake, txt_path.relative_to(config.SUBMISSIONS_DIR).as_posix(),
        {"complete": True, "checked_fields": [], "problems": []})
    message.notify(doc.user_id,
                   f"New submission from Abena Osei for 'Updated contact details form' "
                   f"(22222025_{task_intake}).")

    # A short message thread.
    message.send("11112024", doc.user_id, "Good afternoon Doctor - can my next "
                 "appointment move to a morning slot?")
    message.send(doc.user_id, "11112024", "Morning of the 12th works - I'll update "
                 "the booking today.")

    announcement.create(clinic_id, "Flu vaccination week",
                        "Walk-in flu vaccinations available all next week, 9am-3pm.",
                        urgent=True)
    announcement.create(clinic_id, "New opening hours",
                        "From next month the clinic opens at 7:30am on weekdays.")

    # Appointments: one attended (EP awarded), one missed, one upcoming tomorrow
    # so send_reminders.py has something to do in the demo.
    yesterday_slot = appointment.create(
        clinic_id, "11112024",
        (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M"),
        "Quarterly review")
    appointment.set_status(yesterday_slot, "Attended")
    engagement.on_attendance("11112024")

    missed = appointment.create(
        clinic_id, "22222025",
        (datetime.now() + timedelta(days=30, hours=2)).strftime("%Y-%m-%d %H:%M"),
        "Follow-up consultation")
    appointment.set_status(missed, "No-show")

    appointment.create(clinic_id, "11112024",
                       (datetime.now() + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M"),
                       "Blood test - fasting")

    print("Seeded clinic, 4 accounts, 2 tasks, 2 submissions (1 reviewed), messages,")
    print("2 announcements and 3 appointments.")
    print("Log in as 12350000 / Cl1nic!pass or 11112024 / Pat1ent!aa")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
