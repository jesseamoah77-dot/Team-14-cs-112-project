"""
User accounts: clinicians and patients.

Records live in users.json keyed by the 8-digit user id:

    {
      "12350000": {
        "name": "...", "email": "...", "password": "<bcrypt hash>",
        "role": "clinician", "theme": "dark",
        "engagement": {"points": 0, "streak": 0, "history": []}   # patients only
      }
    }

Passwords are bcrypt-hashed before they ever reach the store. The engagement block is
the patient's private wellness record - routes must only ever expose it to its owner.
"""

import bcrypt

from models import store
from utils.validators import (ValidationError, require, validate_email,
                              validate_password, validate_user_id)


class User:
    def __init__(self, user_id, name, email, role, theme=None, password_hash=None,
                 clinic_id=None, engagement=None):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role
        # Spec: clinicians default to the dark theme; patients start colourful and
        # may switch. Both can change it later in their profile.
        self.theme = theme or ("dark" if role == "clinician" else "colorful")
        self.password_hash = password_hash
        self.clinic_id = clinic_id
        self.engagement = engagement if engagement is not None else (
            {"points": 0, "streak": 0, "history": []} if role == "patient" else None)

    # ---------------------------------------------------------------- persistence

    def to_dict(self):
        record = {
            "name": self.name, "email": self.email, "password": self.password_hash,
            "role": self.role, "theme": self.theme, "clinic_id": self.clinic_id,
        }
        if self.engagement is not None:
            record["engagement"] = self.engagement
        return record

    @classmethod
    def from_dict(cls, user_id, record):
        return cls(
            user_id=user_id, name=record["name"], email=record["email"],
            role=record["role"], theme=record.get("theme"),
            password_hash=record["password"], clinic_id=record.get("clinic_id"),
            engagement=record.get("engagement"),
        )

    def save(self):
        def _apply(data):
            data[self.user_id] = self.to_dict()
        store.update("users", _apply)


def register(user_id, name, email, password, role, clinic_id=None):
    """Validate everything, hash the password, persist, return the User."""
    user_id = validate_user_id(user_id, role)
    name = require(name, "Full name")
    email = validate_email(email)
    validate_password(password)

    if store.load("users").get(user_id):
        raise ValidationError(f"ID {user_id} is already registered.")

    user = User(user_id=user_id, name=name, email=email, role=role, clinic_id=clinic_id)
    user.password_hash = bcrypt.hashpw(password.encode("utf-8"),
                                       bcrypt.gensalt()).decode("utf-8")
    user.save()
    return user


def authenticate(user_id, password):
    """Return the User or raise ValidationError. Same message for every failure mode."""
    record = store.load("users").get((user_id or "").strip())
    if record is None or not bcrypt.checkpw((password or "").encode("utf-8"),
                                            record["password"].encode("utf-8")):
        raise ValidationError("Invalid ID or password.")
    return User.from_dict(user_id.strip(), record)


def get(user_id):
    record = store.load("users").get(user_id)
    return User.from_dict(user_id, record) if record else None


def set_theme(user_id, theme):
    if theme not in ("dark", "colorful"):
        raise ValidationError("Theme must be 'dark' or 'colorful'.")

    def _apply(data):
        if user_id in data:
            data[user_id]["theme"] = theme
    store.update("users", _apply)
