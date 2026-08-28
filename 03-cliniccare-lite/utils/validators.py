"""
Input validation rules from the specification, all in one place.

ID format:
- exactly 8 digits
- clinician IDs end in 0000 (e.g. 12350000)
- patient IDs end in a registration year 2022-2028 (e.g. 12342024)

Passwords: at least 8 characters with an uppercase letter, a lowercase letter, a
digit, and one of !@#$%^&*.
"""

import re

ID_PATTERN = re.compile(r"^\d{8}$")
SPECIAL_CHARS = "!@#$%^&*"


class ValidationError(Exception):
    """Message is written to be shown directly to the user."""


def validate_user_id(user_id, role):
    user_id = (user_id or "").strip()
    if not ID_PATTERN.match(user_id):
        raise ValidationError("ID must be exactly 8 digits.")
    suffix = user_id[-4:]
    if role == "clinician":
        if suffix != "0000":
            raise ValidationError("Clinician IDs must end in 0000 (e.g. 12350000).")
    elif role == "patient":
        if not 2022 <= int(suffix) <= 2028:
            raise ValidationError(
                "Patient IDs must end in a registration year between 2022 and 2028 "
                "(e.g. 12342024).")
    else:
        raise ValidationError(f"Unknown role: {role}")
    return user_id


def validate_password(password):
    password = password or ""
    problems = []
    if len(password) < 8:
        problems.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"\d", password):
        problems.append("a digit")
    if not any(c in SPECIAL_CHARS for c in password):
        problems.append(f"a special character ({SPECIAL_CHARS})")
    if problems:
        raise ValidationError("Password needs " + ", ".join(problems) + ".")
    return password


def validate_email(email):
    email = (email or "").strip()
    # Deliberately simple: something@something.something. Real address verification
    # happens by actually sending mail, not by fighting RFC 5322 with regex.
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValidationError("That doesn't look like a valid email address.")
    return email


def require(value, label):
    if value is None or not str(value).strip():
        raise ValidationError(f"{label} is required.")
    return str(value).strip()
