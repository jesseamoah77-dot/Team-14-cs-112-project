# GridCare-Lite — User Guide

A short walkthrough per role. Demo accounts (created by `seed_demo.py`):

| username | password | role |
|---|---|---|
| `admin1` | `admin123` | Administrator |
| `kwame.e` | `engineer1` | Engineer |
| `ama.t` | `techpass1` | Technician |
| `yaw.t` | `techpass2` | Technician |
| `efua.cs` | `service1` | Customer service |

Start the app from `02-gridcare-lite/`:

```bash
python run.py
```

If it reports an empty database, run `python import_grid_data.py` then
`python seed_demo.py` first.

Each role sees only its own tabs. Trying to do another role's job doesn't just hide
the button — the operation itself is refused, which you can verify from the tests in
`tests/test_gridcare.py`.

---

## Engineer — reporting a fault

1. Log in as `kwame.e`. You land on **Outages**.
2. Click **New outage…** Pick the substation from the list (only real substations
   from the imported grid dataset can be chosen), choose a severity, describe the
   fault, and click **Log outage**.
3. If that substation already has an unresolved outage, the app warns you and asks
   whether this is genuinely a separate incident. This is the duplicate-entry guard.
4. The new outage appears in the table with status **Open**. Select it and click
   **History** at any time to see its full audit trail.

Engineers can also watch work-order progress (read-only) in **Work orders** and the
operational numbers in **Reports**.

## Administrator — dispatching the work

1. Log in as `admin1`. Go to **Work orders**.
2. **Create for outage…** — pick the open outage. A work order is created as
   **Pending**.
3. Select it and click **Assign…** — choose a technician and a scheduled date
   (`YYYY-MM-DD`, today or later; past dates and nonsense dates are refused).
   The order becomes **Scheduled**.

The admin can see every screen, including complaints and the substation register.

## Technician — doing the job

1. Log in as `ama.t`. **My work orders** shows only jobs assigned to *you* —
   another technician's queue is not visible, and acting on someone else's order is
   refused even by id.
2. Select your Scheduled order, click **Start work**. The linked outage moves to
   **In Progress**.
3. When done, click **Complete…** and describe what was actually done (notes are
   required). Completing the order resolves the outage in the same step and stamps
   the resolution time.

## Customer service — logging complaints

1. Log in as `efua.cs`. You land on **Complaints**.
2. **Log complaint…** — record the customer's name, contact and the issue. If the
   complaint matches a known outage, pick it in **Related outage** so operations can
   see how many customers each incident is affecting.
3. The **Outages** tab is available read-only for checking what's already reported.

## Reports

Open, In Progress and Resolved counts, unresolved outages by severity, average
resolution time in hours, complaint totals, and a chart of unresolved outages by
region. The screen re-reads the database every time it's shown, so resolving an
outage in one tab updates the numbers immediately.

---

## The full demo sequence (what we show in the video)

1. `kwame.e` logs the outage →
2. `admin1` creates + assigns the work order →
3. `ama.t` starts, then completes with notes →
4. outage shows **Resolved**; **History** shows every step with who and when →
5. `efua.cs` links a customer complaint →
6. **Reports** shows the moved counts and resolution average.

Error handling worth demonstrating on the way: wrong password, empty outage
description, invalid date (`2026-13-45`), past date, duplicate outage warning,
completing without notes, and a technician trying to start an unassigned order.
