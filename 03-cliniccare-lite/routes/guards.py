"""
Route protection.

Two decorators - clinician_required and patient_required - plus the ownership
helpers the view functions use to scope every data access to the logged-in user.
The rule of thumb throughout the routes: the session tells us who you are, these
helpers decide what of yours a request may touch, and anything else is a 403/404
before any data is read.
"""

from functools import wraps

from flask import abort, redirect, session, url_for

from models import clinic, health_task, task_submission, user


def current_user():
    user_id = session.get("user_id")
    return user.get(user_id) if user_id else None


def _required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            u = current_user()
            if u is None:
                return redirect(url_for("auth.login_page"))
            if u.role != role:
                # Logged in as the other role: not an invitation to guess URLs.
                abort(403)
            return view(u, *args, **kwargs)
        return wrapped
    return decorator


clinician_required = _required("clinician")
patient_required = _required("patient")


def own_clinic_or_403(clinician):
    """The clinic this clinician runs; 403 if they somehow have none."""
    clinic_id, record = clinic.for_clinician(clinician.user_id)
    if clinic_id is None:
        abort(403)
    return clinic_id, record


def own_patient_or_404(clinician, patient_id):
    """A clinician may only touch patients registered to their own clinic."""
    clinic_id, _ = own_clinic_or_403(clinician)
    if not clinic.patient_in_clinic(clinic_id, patient_id):
        abort(404)
    return clinic_id


def own_submission_or_404(u, key):
    """
    Resolve a submission key to a record the caller is entitled to see:
    the submitting patient, or the clinician of the clinic the task belongs to.
    404 rather than 403 for other people's records - don't confirm they exist.
    """
    sub = task_submission.get(key)
    if sub is None:
        abort(404)
    if u.role == "patient":
        if sub["patient_id"] != u.user_id:
            abort(404)
        return sub
    clinic_id, _ = own_clinic_or_403(u)
    task = health_task.get(sub["task_id"])
    if task is None or task["clinic_id"] != clinic_id:
        abort(404)
    return sub


def own_task_or_404(patient, task_id):
    task = health_task.get(task_id)
    if task is None or patient.user_id not in task["assigned_patient_ids"]:
        abort(404)
    return task
