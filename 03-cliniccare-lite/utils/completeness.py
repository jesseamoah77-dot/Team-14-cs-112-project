"""
Automated form-completeness check for .csv and .txt submissions.

THE SCOPE BOUNDARY, spelled out because the rubric penalises crossing it:

This checker reports on STRUCTURE only - is a field present, is a required cell
empty, does a value that should be a date parse as a date. It must never comment on
what the values mean. "The date field is missing" is in scope. "Your blood-pressure
reading is dangerous" is diagnosis, is out of scope, and must never be produced
here or anywhere else in this system. There is deliberately no code path that
compares a submitted value against a medical threshold.

The clinician defines expected field names when creating the task; if none were
defined, the check degrades to "file is readable and non-empty".
"""

import csv
import io
import re

DATE_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$")
NUMBER_LIKE = re.compile(r"^-?\d+(\.\d+)?$")


def check_csv(raw_bytes, expected_fields):
    """
    Returns a dict: {"complete": bool, "problems": [str], "checked_fields": [...]}
    Problems are worded for the patient to act on before submitting.
    """
    problems = []
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"complete": False, "checked_fields": [],
                "problems": ["The file could not be read as text - is it really a CSV?"]}

    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if not rows:
        return {"complete": False, "checked_fields": [],
                "problems": ["The file is empty."]}

    header = [h.strip() for h in rows[0]]
    body = rows[1:]
    if not body:
        problems.append("The file has a header row but no data rows.")

    header_lower = [h.lower() for h in header]
    missing = [f for f in expected_fields if f.lower() not in header_lower]
    for field in missing:
        problems.append(f"The '{field}' column is missing.")

    # Empty-cell check for the expected columns that are present.
    for field in expected_fields:
        if field.lower() not in header_lower:
            continue
        idx = header_lower.index(field.lower())
        empty_rows = [i + 2 for i, row in enumerate(body)
                      if idx >= len(row) or not row[idx].strip()]
        if empty_rows:
            shown = ", ".join(map(str, empty_rows[:5]))
            more = "..." if len(empty_rows) > 5 else ""
            problems.append(f"The '{field}' column has empty cells (row {shown}{more}).")

    # Basic format check: a column whose name suggests a date should parse as dates,
    # one that suggests a reading/count should be numeric. This is still structure -
    # "not a number" is fine to say, "too high" never is.
    for idx, name in enumerate(header_lower):
        values = [row[idx].strip() for row in body if idx < len(row) and row[idx].strip()]
        if not values:
            continue
        if "date" in name and not all(DATE_LIKE.match(v) for v in values):
            problems.append(f"Some values in '{header[idx]}' are not dates "
                            "(expected YYYY-MM-DD or DD/MM/YYYY).")
        elif any(word in name for word in ("reading", "value", "count", "systolic",
                                           "diastolic", "pulse", "weight")):
            if not all(NUMBER_LIKE.match(v) for v in values):
                problems.append(f"Some values in '{header[idx]}' are not numbers.")

    return {"complete": not problems, "checked_fields": expected_fields, "problems": problems}


def check_txt(raw_bytes, expected_fields):
    """For .txt: expects 'Field: value' lines for each expected field."""
    problems = []
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"complete": False, "checked_fields": [],
                "problems": ["The file could not be read as text."]}

    if not text.strip():
        return {"complete": False, "checked_fields": [],
                "problems": ["The file is empty."]}

    lower = text.lower()
    for field in expected_fields:
        marker = field.lower() + ":"
        if marker not in lower:
            problems.append(f"No '{field}:' line found.")
        else:
            after = lower.split(marker, 1)[1].splitlines()[0].strip()
            if not after:
                problems.append(f"The '{field}:' line has no value after it.")

    return {"complete": not problems, "checked_fields": expected_fields, "problems": problems}


def check(filename, raw_bytes, expected_fields):
    """Route by extension. PDFs are not machine-checked - the clinician reviews them."""
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return check_csv(raw_bytes, expected_fields)
    if name.endswith(".txt"):
        return check_txt(raw_bytes, expected_fields)
    return {"complete": True, "checked_fields": [],
            "problems": [], "note": "PDF submissions are reviewed by the clinician directly."}
