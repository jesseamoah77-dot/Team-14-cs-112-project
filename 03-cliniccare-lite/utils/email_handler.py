"""
Email notifications.

With EMAIL_DRY_RUN=1 (the default), emails are appended to data/outbox.json and
printed to the console instead of being sent - so development, tests and demos never
need live SMTP credentials, and the demonstration can show the outbox filling up.
Setting EMAIL_DRY_RUN=0 with real SMTP settings in .env switches to actual sending
over STARTTLS. Credentials only ever come from the environment.

Every send is paired with an in-app notification by the callers (see routes), so a
patient without email access still sees everything in their inbox.
"""

import smtplib
from datetime import datetime
from email.mime.text import MIMEText

import config
from models import store


def send_email(recipient, subject, body):
    """Returns 'sent', 'dry-run', or 'failed: <reason>'. Never raises - a broken
    mail server must not take the review workflow down with it."""
    if config.EMAIL_DRY_RUN:
        def _apply(data):
            entry_id = store.next_id("outbox", "E")
            data[entry_id] = {
                "to": recipient, "subject": subject, "body": body,
                "queued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            return entry_id
        entry = store.update("outbox", _apply)
        print(f"[email dry-run -> outbox {entry}] to={recipient} subject={subject!r}")
        return "dry-run"

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USER
        msg["To"] = recipient
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return "sent"
    except Exception as exc:  # noqa: BLE001 - anything SMTP throws means "not sent"
        print(f"[email failed] to={recipient}: {exc}")
        return f"failed: {exc}"
