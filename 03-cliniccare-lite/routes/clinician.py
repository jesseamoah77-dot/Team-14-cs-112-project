"""
Clinician-facing routes. Every view runs behind clinician_required, and every data
access goes through the ownership helpers - a clinician only ever sees their own
clinic's patients, tasks, submissions and messages.
"""

import csv
import io

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   send_file, url_for)

from models import (announcement, appointment, health_task, message,
                    task_submission, user)
from routes.guards import (clinician_required, own_clinic_or_403,
                           own_patient_or_404, own_submission_or_404)
from utils import analytics, email_handler
from utils.file_handler import open_submission
from utils.validators import ValidationError

bp = Blueprint("clinician", __name__, url_prefix="/clinician")


def _patients_of(record):
    return {pid: user.get(pid) for pid in record["patient_ids"]}


@bp.get("/")
@clinician_required
def dashboard(u):
    clinic_id, record = own_clinic_or_403(u)
    submissions = task_submission.for_clinic(clinic_id)
    pending = {k: s for k, s in submissions.items()
               if s["review"]["outcome"] == "Pending"}
    return render_template(
        "clinician/dashboard.html", user=u, clinic=record, clinic_id=clinic_id,
        patients=_patients_of(record),
        tasks=health_task.for_clinic(clinic_id),
        pending=pending,
        announcements=announcement.active_for_clinic(clinic_id),
        unread=message.unread_count(u.user_id),
    )


@bp.route("/tasks/new", methods=["GET", "POST"])
@clinician_required
def new_task(u):
    clinic_id, record = own_clinic_or_403(u)
    patients = _patients_of(record)
    if request.method == "POST":
        assigned = request.form.getlist("patients")
        assigned = [p for p in assigned if p in record["patient_ids"]]
        fields = [f.strip() for f in request.form.get("expected_fields", "").split(",")]
        try:
            task_id = health_task.create(
                clinic_id, request.form.get("title"), request.form.get("description"),
                request.form.get("due_date"), assigned, expected_fields=fields)
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("clinician/new_task.html", user=u,
                                   patients=patients, form=request.form), 400
        for patient_id in assigned:
            message.notify(patient_id,
                           f"New health task {task_id}: {request.form.get('title')} "
                           f"(due {request.form.get('due_date')}).")
            patient = user.get(patient_id)
            if patient:
                email_handler.send_email(
                    patient.email, f"New health task: {request.form.get('title')}",
                    f"Hello {patient.name},\n\nYour clinician has assigned you a new "
                    f"task, due {request.form.get('due_date')}. Log in to view the "
                    "instructions and submit.\n")
        flash(f"Task {task_id} created and assigned to {len(assigned)} patient(s).",
              "success")
        return redirect(url_for("clinician.dashboard"))
    return render_template("clinician/new_task.html", user=u, patients=patients,
                           form={})


@bp.get("/submissions")
@clinician_required
def submissions(u):
    clinic_id, record = own_clinic_or_403(u)
    subs = task_submission.for_clinic(
        clinic_id,
        task_id=request.args.get("task") or None,
        patient_id=request.args.get("patient") or None,
        outcome=request.args.get("outcome") or None,
    )
    return render_template(
        "clinician/submissions.html", user=u, submissions=subs,
        tasks=health_task.for_clinic(clinic_id), patients=_patients_of(record),
        outcomes=task_submission.REVIEW_OUTCOMES, args=request.args,
        unread=message.unread_count(u.user_id),
    )


@bp.get("/submissions/<key>")
@clinician_required
def submission_detail(u, key):
    sub = own_submission_or_404(u, key)
    task = health_task.get(sub["task_id"])
    patient = user.get(sub["patient_id"])

    preview = None
    path = sub["file_path"]
    if path.endswith((".csv", ".txt")):
        try:
            raw = open_submission(path).read_bytes()
            if path.endswith(".csv"):
                rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))[:21]
                preview = {"kind": "csv", "rows": rows}
            else:
                preview = {"kind": "txt", "text": raw.decode("utf-8-sig")[:5000]}
        except ValidationError:
            preview = {"kind": "missing"}

    return render_template("clinician/submission_detail.html", user=u, key=key,
                           sub=sub, task=task, patient=patient, preview=preview,
                           outcomes=[o for o in task_submission.REVIEW_OUTCOMES
                                     if o != "Pending"])


@bp.post("/submissions/<key>/review")
@clinician_required
def review(u, key):
    sub = own_submission_or_404(u, key)
    outcome = request.form.get("outcome", "")
    notes = request.form.get("notes", "")
    try:
        task_submission.review(key, u.user_id, outcome, notes)
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("clinician.submission_detail", key=key))

    patient = user.get(sub["patient_id"])
    task = health_task.get(sub["task_id"])
    body = (f"Your submission for '{task['title']}' has been reviewed.\n"
            f"Outcome: {outcome}\n" + (f"Notes: {notes}\n" if notes.strip() else ""))
    message.notify(sub["patient_id"], f"Submission reviewed - {outcome}: {task['title']}")
    if patient:
        email_handler.send_email(patient.email, f"Submission reviewed: {task['title']}", body)
    task_submission.mark_notified(key)
    flash(f"Review recorded ({outcome}) and the patient has been notified.", "success")
    return redirect(url_for("clinician.submissions"))


@bp.get("/submissions/<key>/download")
@clinician_required
def download(u, key):
    sub = own_submission_or_404(u, key)
    try:
        path = open_submission(sub["file_path"])
    except ValidationError:
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


@bp.route("/messages/<patient_id>", methods=["GET", "POST"])
@clinician_required
def thread(u, patient_id):
    own_patient_or_404(u, patient_id)
    patient = user.get(patient_id)
    if request.method == "POST":
        try:
            message.send(u.user_id, patient_id, request.form.get("content"))
        except ValidationError as e:
            flash(str(e), "error")
        return redirect(url_for("clinician.thread", patient_id=patient_id))
    for m in message.inbox(u.user_id):
        if m["sender_id"] == patient_id and not m["read"]:
            message.mark_read(u.user_id, m["id"])
    return render_template("thread.html", user=u, other=patient,
                           messages=message.conversation(u.user_id, patient_id),
                           post_url=url_for("clinician.thread", patient_id=patient_id),
                           back_url=url_for("clinician.dashboard"))


@bp.get("/messages/<patient_id>/poll")
@clinician_required
def poll(u, patient_id):
    own_patient_or_404(u, patient_id)
    return {"count": len(message.conversation(u.user_id, patient_id))}


@bp.route("/announcements", methods=["GET", "POST"])
@clinician_required
def announcements(u):
    clinic_id, record = own_clinic_or_403(u)
    if request.method == "POST":
        try:
            announcement.create(
                clinic_id, request.form.get("title"), request.form.get("body"),
                publish_date=request.form.get("publish_date") or None,
                expiry_date=request.form.get("expiry_date") or None,
                urgent=request.form.get("urgent") == "on")
        except ValidationError as e:
            flash(str(e), "error")
            return redirect(url_for("clinician.announcements"))

        if request.form.get("urgent") == "on":
            for patient_id in record["patient_ids"]:
                patient = user.get(patient_id)
                if patient:
                    email_handler.send_email(
                        patient.email, f"Clinic notice: {request.form.get('title')}",
                        request.form.get("body", ""))

        flash("Announcement published.", "success")
        return redirect(url_for("clinician.announcements"))

    return render_template(
        "clinician/announcements.html",
        user=u,
        announcements=announcement.all_for_clinic(clinic_id)
    )


@bp.route("/appointments", methods=["GET", "POST"])
@clinician_required
def appointments(u):
    clinic_id, record = own_clinic_or_403(u)

    if request.method == "POST":
        patient_id = request.form.get("patient_id", "")
        own_patient_or_404(u, patient_id)

        try:
            appointment_id = appointment.create(
                clinic_id,
                patient_id,
                request.form.get("when"),
                request.form.get("purpose")
            )
        except ValidationError as e:
            flash(str(e), "error")
            return redirect(url_for("clinician.appointments"))

        message.notify(
            patient_id,
            f"New appointment {appointment_id}: "
            f"{request.form.get('when')} - {request.form.get('purpose')}"
        )

        patient = user.get(patient_id)

        if patient:
            email_handler.send_email(
                patient.email,
                "New appointment booked",
                f"Hello {patient.name},\n\nYou have an appointment on "
                f"{request.form.get('when')}: {request.form.get('purpose')}.\n"
            )

        flash(
            "Appointment created and the patient notified.",
            "success"
        )

        return redirect(
            url_for("clinician.appointments")
        )

    return render_template(
        "clinician/appointments.html",
        user=u,
        appointments=appointment.for_clinic(clinic_id),
        patients=_patients_of(record)
    )


@bp.post("/appointments/<appointment_id>/status")
@clinician_required
def appointment_status(u, appointment_id):
    clinic_id, _ = own_clinic_or_403(u)

    record = appointment.for_clinic(
        clinic_id
    ).get(appointment_id)

    if record is None:
        abort(404)

    status = request.form.get(
        "status",
        ""
    )

    try:
        appointment.set_status(
            appointment_id,
            status,
            clinic_id=clinic_id,
            user_role=u.role,
        )

    except ValidationError as e:
        flash(
            str(e),
            "error"
        )

        return redirect(
            url_for("clinician.appointments")
        )

    if status == "Attended":
        from utils import engagement
        engagement.on_attendance(
            record["patient_id"]
        )

    flash(
        f"Appointment marked {status}.",
        "success"
    )

    return redirect(
        url_for("clinician.appointments")
    )


@bp.get("/analytics")
@clinician_required
def analytics_view(u):
    clinic_id, _ = own_clinic_or_403(u)
    return render_template(
        "clinician/analytics.html",
        user=u,
        stats=analytics.clinic_summary(clinic_id)
    )
