"""
ClinicCare-Lite - Flask application.

    python app.py            (development server on http://localhost:5000)

Needs a .env with FLASK_SECRET_KEY set (copy .env.example). Refuses to start
without one rather than falling back to a guessable default.
"""

from datetime import timedelta

from flask import Flask, render_template

import config


def create_app():
    if not config.SECRET_KEY:
        raise RuntimeError(
            "FLASK_SECRET_KEY is not set. Copy .env.example to .env and generate a "
            "key:  python -c \"import secrets; print(secrets.token_hex(32))\"")

    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES
    app.permanent_session_lifetime = timedelta(minutes=config.SESSION_LIFETIME_MINUTES)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


    from routes import auth, clinician, patient
    app.register_blueprint(auth.bp)
    app.register_blueprint(clinician.bp)
    app.register_blueprint(patient.bp)
    
    @app.context_processor
    def inject_today():
        # Templates compare due/expiry dates against "today" (overdue badges,
        # expired announcements) - one definition of today, injected everywhere.
        from datetime import date
        return {"now_date": date.today().isoformat()}

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               title="Not allowed",
                               detail="Your account does not have access to that page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404,
                               title="Not found",
                               detail="That page or record does not exist."), 404

    @app.errorhandler(413)
    def too_large(_e):
        limit = config.MAX_UPLOAD_BYTES // 1024 // 1024
        return render_template("error.html", code=413,
                               title="File too large",
                               detail=f"Uploads are limited to {limit} MB."), 413

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", code=500,
                               title="Something went wrong",
                               detail="The error has been logged. Try again."), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
