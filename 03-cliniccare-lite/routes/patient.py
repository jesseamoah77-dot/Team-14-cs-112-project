"""
Patient-facing routes. Scoping rule: everything on these pages belongs to the
logged-in patient - their tasks, their submissions, their inbox, their engagement,
their clinician. Other patients' records are unreachable by construction (the
ownership helpers 404 on anything that isn't theirs).
"""

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   send_file, url_for)

from models import (announcement, appointment, clinic, health_task, message,
                    task_submission, user)
from routes.guards import own_submission_or_404, own_task_or_404, patient_required
from utils import analytics, email_handler, engagement
from utils.completeness import check as completeness_check
from utils.file_handler import open_submission, save_submission
from utils.validators import ValidationError

bp = Blueprint("patient", __name__, url_prefix="/patient")


def _my_clinician(patient):
    record = clinic.get(patient.clinic_id)
    return user.get(record["clinician_id"]) if record else None


@bp.get("/")
@patient_required
def dashboard(u):
    tasks = health_task.for_patient(u.user_id)
    submissions = task_submission.for_patient(u.user_id)
    for task_id, task in tasks.items():
        task["submission"] = submissions.get(f"{u.user_id}_{task_id}")
    return render_template(
        "patient/dashboard.html", user=u, tasks=tasks,
        announcements=announcement.active_for_clinic(u.clinic_id) if u.clinic_id else [],
        appointments={aid: a for aid, a in appointment.for_patient(u.user_id).items()
                      if a["status"] == "Scheduled"},
        unread=message.unread_count(u.user_id),
        clinician=_my_clinician(u),
    )


# ---------------------------------------------------------------- submitting

@bp.route("/tasks/<task_id>/submit", methods=["GET", "POST"])
@patient_required
def submit(u, task_id):
    task = own_task_or_404(u, task_id)
    if request.method == "POST":
        uploaded = request.files.get("file")
        try:
            # Completeness first, on the raw bytes: reject-with-reasons before
            # anything is stored. Structure only - see utils/completeness.py.
            raw = uploaded.read() if uploaded else b""
            if uploaded:
                uploaded.stream.seek(0)
            result = completeness_check(uploaded.filename if uploaded else "",
                                        raw, task.get("expected_fields", []))
            if not result["complete"]:
                for problem in result["problems"]:
                    flash(problem, "error")
                flash("Fix the issues above and submit again - nothing was stored.",
                      "error")
                return render_template("patient/submit.html", user=u, task=task,
                                       task_id=task_id), 400

            path = save_submission(uploaded, u.clinic_id, u.user_id, task_id)
            key = task_submission.record(u.user_id, task_id, path, result)
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("patient/submit.html", user=u, task=task,
                                   task_id=task_id), 400

        on_time = engagement.on_submission(u.user_id, task["due_date"],
                                           task_submission.get(key)["submitted_at"])
        message.notify(u.user_id,
                       f"Submission received for '{task['title']}'"
                       + (" - on time." if on_time else " (after the due date)."))
        clinician = _my_clinician(u)
        if clinician:
            message.notify(clinician.user_id,
                           f"New submission from {u.name} for '{task['title']}' "
                           f"({key}).")
            email_handler.send_email(
                clinician.email, f"New submission: {task['title']}",
                f"Patient {u.name} ({u.user_id}) submitted task {task_id}. "
                "Log in to review it.")
        flash("Submission received - you'll be notified when it has been reviewed.",
              "success")
        return redirect(url_for("patient.dashboard"))
    return render_template("patient/submit.html", user=u, task=task, task_id=task_id)


@bp.get("/submissions/<key>/download")
@patient_required
def download(u, key):
    sub = own_submission_or_404(u, key)
    try:
        path = open_submission(sub["file_path"])
    except ValidationError:
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


# ---------------------------------------------------------------- inbox + messaging

@bp.get("/inbox")
@patient_required
def inbox(u):
    items = message.inbox(u.user_id)
    for m in items:
        if not m["read"]:
            message.mark_read(u.user_id, m["id"])
    return render_template("patient/inbox.html", user=u, items=items)


@bp.route("/messages", methods=["GET", "POST"])
@patient_required
def thread(u):
    clinician = _my_clinician(u)
    if clinician is None:
        flash("Your clinic has no clinician assigned yet.", "error")
        return redirect(url_for("patient.dashboard"))
    if request.method == "POST":
        try:
            message.send(u.user_id, clinician.user_id, request.form.get("content"))
        except ValidationError as e:
            flash(str(e), "error")
        return redirect(url_for("patient.thread"))
    return render_template("thread.html", user=u, other=clinician,
                           messages=message.conversation(u.user_id, clinician.user_id),
                           post_url=url_for("patient.thread"),
                           back_url=url_for("patient.dashboard"))


# ---------------------------------------------------------------- private views

@bp.get("/messages/poll")
@patient_required
def poll(u):
    """Message count for the thread page's near-real-time refresh (periodic
    polling - the spec's lighter alternative to WebSockets)."""
    clinician = _my_clinician(u)
    if clinician is None:
        return {"count": 0}
    return {"count": len(message.conversation(u.user_id, clinician.user_id))}


@bp.get("/engagement")
@patient_required
def engagement_view(u):
    return render_template("patient/engagement.html", user=u,
                           summary=engagement.summary(u.user_id))


@bp.get("/history")
@patient_required
def history(u):
    return render_template("patient/history.html", user=u,
                           history=analytics.patient_history(u.user_id))
