# ClinicCare-Lite — Clinician Guide

Demo account: ID `12350000`, password `Cl1nic!pass` (created by `seed_demo.py`).
Start the app from `03-cliniccare-lite/` with `python app.py` and open
http://localhost:5000.

## Registering (first use)

Choose **Clinician** on the registration page. Your ID must be 8 digits ending in
`0000`. Registering creates your clinic with the name you enter — patients then pick
it when they register. Your interface defaults to the dark theme; the navbar button
switches it.

## Dashboard

Cards for submissions awaiting review, active tasks, unread messages and current
announcements, plus your task list and patient register. **Review now** jumps
straight to the pending queue.

## Assigning a health task

**New health task** → title, instructions, due date, and tick the patients. Two
things worth knowing:

- **Expected fields** (optional, comma-separated — e.g. `Date, Systolic`) drive the
  automated completeness check on `.csv`/`.txt` submissions. The check is
  structural only: it tells the patient a column is missing or a cell is empty. It
  never reads meaning into the values — that is your job, not the system's.
- Every assigned patient is notified in-app and by email on creation.

## Reviewing submissions

**Submissions** lists everything from your clinic, filterable by task, patient and
status. Open one to see the file inline (`.csv` as a table, `.txt` as text, `.pdf`
via download), any completeness warnings, and the review form.

Reviews are **categorical** — Reviewed – Normal / Needs Follow-up / Escalated — plus
free-text notes. There is deliberately no score field: these are health-related
records, not graded work. Saving the review notifies the patient in-app and by
email, and records you as the reviewer with a timestamp.

A patient can replace their file **before** you review it (the list marks it
"resubmitted"); after your review the submission is locked.

## Messaging and announcements

**Message** next to a patient opens your thread with them. Threads are private to
the two of you, refresh automatically every few seconds, and carry a permanent
notice that the channel is not monitored continuously and is not for emergencies.

**Announcements** publishes to every patient dashboard, with optional publish/expiry
dates. Ticking **Urgent** also emails every registered patient.

## Appointments and analytics

**Appointments**: book with `YYYY-MM-DD HH:MM` (future only — past times are
refused); the patient is notified. Afterwards mark **Attended / No-show /
Cancel** — attendance feeds the no-show analytics and the patient's private
engagement record. Reminders go out via `python send_reminders.py` (schedule it
hourly, or run it by hand in a demo — each appointment is reminded exactly once,
24 hours ahead).

**Analytics** shows clinic-level aggregates only: completion rate, pending reviews,
average review turnaround, overdue assignments, weekly no-show rate, monthly task
volume and outcome counts. No individual patient is named or ranked anywhere on
this page — that is by design, not an omission.
