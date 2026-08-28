"""Login, registration, logout, theme switching."""

from flask import (Blueprint, flash, redirect, render_template, request, session,
                   url_for)

from models import clinic, user
from routes.guards import current_user
from utils.validators import ValidationError

bp = Blueprint("auth", __name__)


@bp.get("/")
def login_page():
    u = current_user()
    if u is not None:
        return redirect(url_for(f"{u.role}.dashboard"))
    return render_template("login.html")


@bp.post("/login")
def login():
    try:
        u = user.authenticate(request.form.get("user_id"), request.form.get("password"))
    except ValidationError as e:
        flash(str(e), "error")
        return render_template("login.html"), 401
    session.clear()
    session["user_id"] = u.user_id
    session.permanent = True
    return redirect(url_for(f"{u.role}.dashboard"))


@bp.get("/register")
def register_page():
    return render_template("register.html", clinics=clinic.list_all())


@bp.post("/register")
def register():
    form = request.form
    role = form.get("role", "")
    try:
        if role == "clinician":
            u = user.register(form.get("user_id"), form.get("name"), form.get("email"),
                              form.get("password"), "clinician")
            clinic_id = clinic.create(form.get("clinic_name"), u.user_id)
            u.clinic_id = clinic_id
            u.save()
        elif role == "patient":
            clinic_id = form.get("clinic_id", "")
            if not clinic.get(clinic_id):
                raise ValidationError("Choose the clinic you are registered with.")
            u = user.register(form.get("user_id"), form.get("name"), form.get("email"),
                              form.get("password"), "patient", clinic_id=clinic_id)
            clinic.add_patient(clinic_id, u.user_id)
        else:
            raise ValidationError("Choose a role.")
    except ValidationError as e:
        flash(str(e), "error")
        return render_template("register.html", clinics=clinic.list_all(),
                               form=form), 400
    flash("Registration successful - log in with your ID.", "success")
    return redirect(url_for("auth.login_page"))


@bp.get("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login_page"))


@bp.post("/theme")
def set_theme():
    u = current_user()
    if u is None:
        return redirect(url_for("auth.login_page"))
    try:
        user.set_theme(u.user_id, request.form.get("theme", ""))
    except ValidationError as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for(f"{u.role}.dashboard"))
