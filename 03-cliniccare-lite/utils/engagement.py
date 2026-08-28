"""
Private wellness-engagement tracker.

Deliberately NOT a leaderboard. The brief's own design note explains why: ranking
patients - even anonymised - leaks who is and isn't keeping up with appointments or
tasks, which is exactly what patient confidentiality protects. So:

- points/streaks live inside the owner's user record only
- the only read function takes the owner's id and returns only their record
- there is no function here that reads engagement across users, and the analytics
  module must never aggregate this data into anything patient-comparable

Earning rules (documented for the report): +10 EP for a task submitted on or before
its due date, +5 EP for an attended appointment. Streak counts consecutive on-time
submissions and resets on a late one.
"""

from datetime import datetime

from models import store

ON_TIME_SUBMISSION_EP = 10
ATTENDED_APPOINTMENT_EP = 5


def _award(patient_id, points, reason, streak_action=None):
    def _apply(data):
        record = data.get(patient_id)
        if not record or record.get("role") != "patient":
            return
        engagement = record.setdefault("engagement",
                                       {"points": 0, "streak": 0, "history": []})
        engagement["points"] += points
        if streak_action == "increment":
            engagement["streak"] += 1
        elif streak_action == "reset":
            engagement["streak"] = 0
        engagement["history"].append({
            "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "points": points, "reason": reason,
        })
    store.update("users", _apply)


def on_submission(patient_id, task_due_date, submitted_at):
    """Award for an on-time submission; late ones just reset the streak."""
    on_time = submitted_at[:10] <= task_due_date
    if on_time:
        _award(patient_id, ON_TIME_SUBMISSION_EP, "Task submitted on time", "increment")
    else:
        _award(patient_id, 0, "Task submitted late", "reset")
    return on_time


def on_attendance(patient_id):
    _award(patient_id, ATTENDED_APPOINTMENT_EP, "Appointment attended")


def summary(patient_id):
    """The owner's own record - points, streak, and a this-month rollup."""
    record = store.load("users").get(patient_id)
    if not record or "engagement" not in record:
        return {"points": 0, "streak": 0, "this_month": 0, "history": []}
    engagement = record["engagement"]
    month = datetime.now().strftime("%Y-%m")
    this_month = sum(h["points"] for h in engagement["history"]
                     if h["at"].startswith(month))
    return {"points": engagement["points"], "streak": engagement["streak"],
            "this_month": this_month, "history": engagement["history"][-20:]}
