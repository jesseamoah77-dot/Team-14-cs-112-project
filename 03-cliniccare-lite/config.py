"""
Configuration for ClinicCare-Lite.

Secrets come from the environment (a local .env file loaded by python-dotenv), never
from source code. Copy .env.example to .env and fill it in - the app refuses to start
without a real FLASK_SECRET_KEY so nobody accidentally demos with a default key.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SUBMISSIONS_DIR = BASE_DIR / "submissions"

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "")

# Email settings. EMAIL_DRY_RUN=1 (the default) writes emails to data/outbox.json and
# the console instead of talking to an SMTP server - right for development and demos.
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_DRY_RUN = os.environ.get("EMAIL_DRY_RUN", "1") == "1"

# File-upload rules from the spec: .txt/.csv/.pdf only. The spec says "file-size
# restrictions" without a number; 5 MB comfortably covers a symptom log or a scanned
# referral letter while keeping a runaway upload out.
ALLOWED_EXTENSIONS = {".txt", ".csv", ".pdf"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

SESSION_LIFETIME_MINUTES = 30
