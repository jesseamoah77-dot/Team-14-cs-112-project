"""
Operational analytics.

Two strictly separated views:

- clinic_summary(clinic_id): aggregates for the clinician - counts and rates over
  their own clinic only. Nothing here identifies how one patient compares to
  another, and engagement data is never touched.
- patient_history(patient_id): one patient's own record for their own dashboard.

Everything is computed from tasks/submissions/appointments on demand - no cached
numbers to go stale.
"""

from collections import defaultdict
from datetime import datetime

from models import appointment, health_task, store, task_submission


def _dt(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")


def clinic_summary(clinic_id):
    tasks = health_task.for_clinic(clinic_id)
    submissions = task_submission.for_clinic(clinic_id)
    appointments = appointment.for_clinic(clinic_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # Task completion: of every (task, assigned patient) pair, how many have a submission?
    expected = sum(len(t["assigned_patient_ids"]) for t in tasks.values())
    completed = len(submissions)
    completion_rate = round(100 * completed / expected, 1) if expected else None

    pending_reviews = sum(1 for s in submissions.values()
                          if s["review"]["outcome"] == "Pending")

    # Review turnaround: submission -> review, averaged over reviewed submissions.
    turnarounds = [
        (_dt(s["review"]["reviewed_at"]) - _dt(s["submitted_at"])).total_seconds() / 3600
        for s in submissions.values() if s["review"]["reviewed_at"]
    ]
    avg_turnaround_hours = round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else None

    # Overdue: assigned pairs past the task due date with no submission yet.
    overdue = 0
    for task_id, t in tasks.items():
        if t["due_date"] >= today:
            continue
        for patient_id in t["assigned_patient_ids"]:
            if f"{patient_id}_{task_id}" not in submissions:
                overdue += 1

    # No-show rate by week, from appointments whose attendance was recorded.
    weekly = defaultdict(lambda: {"attended": 0, "no_show": 0})
    for a in appointments.values():
        week = datetime.strptime(a["when"], "%Y-%m-%d %H:%M").strftime("%Y-W%W")
        if a["status"] == "Attended":
            weekly[week]["attended"] += 1
        elif a["status"] == "No-show":
            weekly[week]["no_show"] += 1
    no_show_by_week = []
    for week in sorted(weekly):
        counts = weekly[week]
        total = counts["attended"] + counts["no_show"]
        no_show_by_week.append({
            "week": week, **counts,
            "no_show_rate": round(100 * counts["no_show"] / total, 1) if total else 0.0,
        })

    monthly_volume = defaultdict(int)
    for t in tasks.values():
        monthly_volume[t["created_at"][:7]] += 1

    outcome_counts = defaultdict(int)
    for s in submissions.values():
        outcome_counts[s["review"]["outcome"]] += 1

    return {
        "tasks_total": len(tasks),
        "assignments_expected": expected,
        "submissions_received": completed,
        "completion_rate_pct": completion_rate,
        "pending_reviews": pending_reviews,
        "avg_review_turnaround_hours": avg_turnaround_hours,
        "overdue_assignments": overdue,
        "no_show_by_week": no_show_by_week,
        "monthly_task_volume": dict(sorted(monthly_volume.items())),
        "review_outcomes": dict(outcome_counts),
    }


def patient_history(patient_id):
    """This patient's own tasks, submissions and appointments - nobody else's."""
    tasks = health_task.for_patient(patient_id)
    submissions = task_submission.for_patient(patient_id)
    appointments = appointment.for_patient(patient_id)
    today = datetime.now().strftime("%Y-%m-%d")

    timeline = []
    for task_id, t in sorted(tasks.items(), key=lambda kv: kv[1]["due_date"]):
        submission = submissions.get(f"{patient_id}_{task_id}")
        if submission:
            status = ("On time" if submission["submitted_at"][:10] <= t["due_date"]
                      else "Late")
        else:
            status = "Overdue" if t["due_date"] < today else "Not yet submitted"
        timeline.append({
            "task_id": task_id, "title": t["title"], "due_date": t["due_date"],
            "status": status,
            "review": submission["review"]["outcome"] if submission else None,
        })

    attended = sum(1 for a in appointments.values() if a["status"] == "Attended")
    no_show = sum(1 for a in appointments.values() if a["status"] == "No-show")

    return {
        "timeline": timeline,
        "tasks_assigned": len(tasks),
        "tasks_submitted": len(submissions),
        "appointments_attended": attended,
        "appointments_missed": no_show,
    }
