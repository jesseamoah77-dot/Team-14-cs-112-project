# ClinicCare-Lite — Patient Guide

Demo account: ID `11112024`, password `Pat1ent!aa` (created by `seed_demo.py`).
Open http://localhost:5000 while the app is running.

## Registering

Choose **Patient**, pick your clinic from the list, and enter your 8-digit ID — it
ends in your registration year, between 2022 and 2028 (e.g. `12342024`). Passwords
need at least 8 characters with an uppercase letter, a lowercase letter, a digit and
one of `!@#$%^&*` — the form shows you live what's still missing.

## Your dashboard

Everything in one place: clinic announcements at the top (urgent ones highlighted),
your upcoming appointments, and a card per health task showing its status — Not
submitted, Overdue, or the review outcome once your clinician has looked at it,
along with any notes they wrote you.

The **Dark/Light** button in the navbar switches your theme; your choice is saved.

## Submitting a task

Open a task and choose your file. The rules:

- **`.txt`, `.csv` or `.pdf` only**, up to 5 MB.
- If the task lists expected fields (say `Date, Systolic`), the system checks your
  file has them before accepting it. If something is missing you'll get told exactly
  what — "The 'Systolic' column is missing" — and nothing is stored until you fix
  it. The system only checks the file's *structure*; it never reads or interprets
  your health information.
- Submitting on or before the due date earns you engagement points (see below).

You'll get a confirmation in your inbox, and your clinician is notified. You can
replace your file any time **before** it's reviewed; after review it's locked — ask
your clinician if it needs changing.

## Inbox and messages

**Inbox** collects everything the system sends you: submission confirmations,
review outcomes, appointment notices and reminders.

**Messages** is your private thread with your clinician, for non-urgent things like
rescheduling. It refreshes itself every few seconds. The warning on that page is
real: **the thread is not watched around the clock — never use it for anything
urgent.** In an emergency contact emergency services directly.

Nobody but you and your clinician can read your thread, and you can never see
another patient's anything — records, files, messages or progress.

## My progress and my history

**My progress** is your private engagement record: +10 points for each on-time task
submission, +5 for each attended appointment, and your current on-time streak. Only
you can see this page — there is no leaderboard and no comparison with other
patients, deliberately.

**My history** lists your own tasks (on time / late / overdue) and your attendance
record — your data only.
