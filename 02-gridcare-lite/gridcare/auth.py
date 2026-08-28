"""
Authentication for GridCare-Lite.

Passwords are bcrypt-hashed before storage - never stored or compared in plain text.
bcrypt does its own salting, so two users with the same password still get different
hashes, and verification uses checkpw rather than string comparison.
"""

from datetime import datetime

import bcrypt

ROLES = ("admin", "engineer", "technician", "customer_service")

# Kept deliberately lighter than ClinicCare-Lite's password policy: this is an internal
# staff tool where accounts are created by an administrator, not self-service signup.
MIN_PASSWORD_LENGTH = 6


class AuthError(Exception):
    """Bad credentials or an account problem. Message is safe to show in the UI."""


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_user(conn, username, password, full_name, role):
    username = (username or "").strip()
    if not username:
        raise AuthError("Username is required.")
    if role not in ROLES:
        raise AuthError(f"Unknown role: {role}")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not (full_name or "").strip():
        raise AuthError("Full name is required.")

    existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        raise AuthError(f"Username '{username}' is already taken.")

    cur = conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        (username, hash_password(password), full_name.strip(), role),
    )
    conn.commit()
    return cur.lastrowid


def authenticate(conn, username, password):
    """
    Return the user row on success, raise AuthError otherwise.

    Same error message for unknown user and wrong password on purpose: a login screen
    that says "no such user" tells an attacker which usernames exist.
    """
    row = conn.execute(
        "SELECT user_id, username, password_hash, full_name, role FROM users WHERE username = ?",
        ((username or "").strip(),),
    ).fetchone()

    if row is None or not bcrypt.checkpw((password or "").encode("utf-8"),
                                         row["password_hash"].encode("utf-8")):
        raise AuthError("Invalid username or password.")
    return row


def now_iso():
    """One timestamp format everywhere: 'YYYY-MM-DD HH:MM:SS' (sorts correctly as text)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
