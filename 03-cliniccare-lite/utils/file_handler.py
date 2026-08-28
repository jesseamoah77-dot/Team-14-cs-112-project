"""
Secure storage of patient submissions.

Rules from the spec, enforced here in one place:
- only .txt / .csv / .pdf
- renamed to patientID_taskID.extension
- stored under submissions/<clinic_id>/<patient_id>/
- size-limited (config.MAX_UPLOAD_BYTES)

Path traversal: every path component we build comes from values we generated
ourselves (validated 8-digit ids, T-prefixed task ids) - never from a client-supplied
filename. The uploaded name's only contribution is its extension, and that is checked
against the allow-list. As a belt-and-braces check, the final resolved path must stay
inside SUBMISSIONS_DIR or we refuse.
"""

from pathlib import Path

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, SUBMISSIONS_DIR
from utils.validators import ValidationError


def check_extension(filename):
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationError(f"Only {allowed} files are accepted (got '{ext or 'no extension'}').")
    return ext


def save_submission(file_storage, clinic_id, patient_id, task_id):
    """
    Validate and store an uploaded file (a Werkzeug FileStorage). Returns the path
    relative to SUBMISSIONS_DIR, which is what gets recorded in the submission.
    """
    if file_storage is None or not file_storage.filename:
        raise ValidationError("Choose a file to upload.")
    ext = check_extension(file_storage.filename)

    # Size check without trusting Content-Length: seek to the end of the stream.
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size == 0:
        raise ValidationError("That file is empty.")
    if size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File is {size / 1024 / 1024:.1f} MB - the limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB.")

    directory = Path(SUBMISSIONS_DIR) / clinic_id / patient_id
    target = directory / f"{patient_id}_{task_id}{ext}"

    # Refuse anything that escapes the submissions root, however it got there.
    root = Path(SUBMISSIONS_DIR).resolve()
    if root not in target.resolve().parents:
        raise ValidationError("Invalid storage path.")

    directory.mkdir(parents=True, exist_ok=True)
    file_storage.save(target)
    # Store with forward slashes so the JSON is identical on Windows and Linux
    # (and the templates can split on '/' for the display name).
    return target.relative_to(root).as_posix()


def open_submission(relative_path):
    """Resolve a stored relative path back to an absolute one, safely."""
    root = Path(SUBMISSIONS_DIR).resolve()
    target = (root / relative_path).resolve()
    if root not in target.parents:
        raise ValidationError("Invalid file path.")
    if not target.exists():
        raise ValidationError("The submitted file is missing from storage.")
    return target
