# ClinicCare-Lite — Technical Report

CS 112 Final Course Project, Component 3 · Summer 2026

---

## 1. What the system is

ClinicCare-Lite is a clinic **administration and communication** web application:
clinicians assign health-related administrative tasks, patients submit files,
clinicians review them with categorical outcomes, and both sides communicate through
notifications, messaging, announcements and appointment reminders.

**Scope boundary (hard requirement, enforced throughout):** the system schedules,
collects and routes information. It never diagnoses, interprets symptoms, scores
health data or recommends treatment. Concretely:

- review outcomes are categorical (Pending / Reviewed – Normal / Needs Follow-up /
  Escalated) and set only by a clinician; the code rejects a numeric grade as an
  invalid outcome (tested);
- the automated form check reports **structure only** — "the Systolic column is
  missing", never "your reading is high". A test submits a clinically alarming value
  and asserts the checker says nothing about it;
- there is no code path anywhere that compares a submitted health value against a
  threshold.

## 2. Requirements coverage

Every item on the brief's minimum-acceptance list (§9) is implemented and covered by
at least one automated test: registration and login with the ID rules, role
restrictions, bcrypt hashing, task creation/assignment, patient viewing and file
submission, file-type validation, clinician review with categorical outcomes,
patient access to results, persistent JSON storage, messaging and notifications,
protection against cross-patient access, an analytics view, unit + integration
tests, and the non-diagnostic boundary.

Two gaps in the specification were identified and resolved: the spec requires appointment reminders and
no-show analytics but lists no storage file for appointments, and specifies
announcements with no storage either. `appointments.json` and `announcements.json`
were added.

## 3. Architecture

Flask, three layers, JSON persistence:

```
routes/     auth, clinician, patient blueprints; guards.py = access control
models/     store (persistence) + one module per entity
utils/      validators, file_handler, completeness, engagement, analytics, email
templates/  Jinja2 + Bootstrap; static/ = two themes + client-side validation
```

Decisions worth defending at the oral:

- **All access control is concentrated in `routes/guards.py`** — two role decorators
  plus ownership helpers (`own_submission_or_404`, `own_patient_or_404`,
  `own_task_or_404`). Every view resolves records through them, so "patient A reads
  patient B's file" is impossible by construction, not by remembering to check.
  Foreign records return **404, not 403**, so responses don't confirm that a record
  exists.
- **`models/store.py` is the only code that touches disk.** Writes go to a temp file
  then `os.replace()` — atomic, so a crash mid-write cannot corrupt a JSON file.
  This also covers the truncation bug the brief documents (writing a shorter payload
  over a longer one in `r+` mode leaves trailing bytes); a test writes big, writes
  small, and re-reads clean. A re-entrant lock serialises load-modify-save against
  Flask's threaded request handling.
- **Client-side validation duplicates, never replaces, server checks.** The live
  password feedback and extension check in `static/scripts.js` are convenience;
  disabling JavaScript changes nothing about what the server accepts.

## 4. Security controls

| control | implementation |
|---|---|
| Password storage | bcrypt with per-password salt; complexity rules from the spec (8+, upper, lower, digit, special) |
| ID validation | regex: 8 digits; clinician `*0000`; patient suffix 2022–2028 |
| Login errors | identical message for unknown ID and wrong password (no account enumeration) |
| Sessions | Flask signed cookie, HttpOnly, SameSite=Lax, 30-minute lifetime |
| Secrets | `.env` only (git-ignored); app refuses to start without `FLASK_SECRET_KEY`; no credentials in source |
| Uploads | extension allow-list (.txt/.csv/.pdf), 5 MB cap measured from the stream, renamed to `patientID_taskID.ext`, stored under `submissions/clinic/patient/` |
| Path traversal | stored paths are built only from validated IDs; every resolved path must stay inside the submissions root or the request is refused |
| Cross-patient access | ownership helpers scope every read; conversations are strictly pairwise; inbox returns recipient-only; engagement is readable only by its owner |
| Messaging safety | persistent "not monitored continuously — not for emergencies" notice on every thread view (spec requirement, asserted in a test) |

## 5. Key workflows

**Task → submission → review → notification.** Clinician creates a task (title,
instructions, due date, optional expected fields) → assigned patients get an in-app
notification and an email → patient uploads → the completeness check runs on the raw
bytes *before* anything is stored, and an incomplete file is rejected with named,
actionable problems → on acceptance the file is stored and recorded, the patient
gets a confirmation, the clinician gets a notification and email → clinician reviews
with an outcome + notes → patient is notified in-app and by email, and the outcome
plus notes appear on their dashboard. Resubmission is allowed before review
(flagged), blocked after (tested).

**Appointments.** Clinician books (validated future date-time) → patient notified →
`send_reminders.py` sends 24-hour reminders exactly once per appointment → clinician
marks Attended/No-show afterwards, which feeds the weekly no-show analytics and, for
attendance, the patient's private engagement record.

**Engagement (deliberately not a leaderboard).** +10 EP for an on-time submission,
+5 for attendance, streak resets on a late submission. Points live inside the
owner's user record; the module exposes exactly one read — `summary(patient_id)` —
and a test asserts no ranking/comparison function exists. The brief's own rationale
applies: ranking patients, even anonymised, leaks who is and isn't keeping up with
their care.

**Email.** `EMAIL_DRY_RUN=1` (default) appends to `data/outbox.json` so demos and
tests need no SMTP account; production mode reads credentials from the environment
and sends over STARTTLS. A mail failure logs and returns — it never takes the review
workflow down.

## 6. Testing

134 automated tests across the repo; ClinicCare-Lite accounts for 83:

- **59 model/utility tests** — ID and password rules (parametrised valid/invalid),
  store atomicity, registration/login, task rules, submission/review transitions,
  messaging privacy, appointment windows, announcement publish/expiry, engagement
  arithmetic and privacy, analytics arithmetic and scoping.
- **24 route tests** (Flask test client) — login routes by role; unauthenticated
  requests redirect; patient→clinician URLs 403; cross-patient submission download
  404s while own download 200s; the full submit-review-notify loop including the
  outbox; incomplete CSV rejected naming the missing column; wrong extension
  rejected; the emergency notice present; the analytics page never naming a patient.

Manual browser verification walked the full demo sequence and additionally probed
the running app with direct `fetch()` calls for the three access-control cases
(404/200/403 — all correct).

## 7. Defects found and fixed during development

Six defects were logged during development. Highlights: a check-ordering bug in
GridCare's `start_work` (found by writing tests), Windows path separators leaking
into stored submission records (found by walking the UI, invisible to the tests —
which is exactly why both kinds of testing exist), and a factual error in analysis
prose corrected against computed output.

## 8. Known limitations

- JSON files are fine for a coursework prototype but have no indexing or
  concurrent-writer story beyond the in-process lock; the natural upgrade is SQLite
  (the store module's interface was designed so models wouldn't change).
- Single clinician per clinic; no admin role for managing clinics.
- Polling (5 s) rather than WebSockets for messaging — the spec allows either; the
  simpler one was chosen deliberately.
- Email dry-run is the default; live SMTP was intentionally not exercised in
  development to keep credentials out of the project entirely.
- No password-reset flow (out of the spec's scope; would need an email token flow).

## 9. Future work

SQLite migration behind the existing store interface; multi-clinician clinics with
an admin role; patient self-scheduling of appointments from published slots; file
virus-scanning hook on upload; audit log of clinician record access; accessibility
audit beyond Bootstrap defaults.
