"""
JSON persistence for ClinicCare-Lite.

All reads and writes for the data/*.json files go through this module, for two
reasons that came out of the project brief itself:

1. The brief documents a real bug in the naive save pattern: opening a file 'r+',
   seeking to 0 and writing a *shorter* payload leaves trailing bytes of the old
   content behind, corrupting the JSON ("Extra data" on the next read). The usual fix
   is truncate(); we go one step further and write to a temp file then os.replace()
   it - atomic on both Windows and POSIX - so a crash mid-write can't leave a
   half-written file either.

2. Flask handles requests on threads. A lock around load-modify-save keeps two
   simultaneous requests from silently losing one of their writes.

Files are created empty ({}) on first use, so a fresh checkout works without any
manual setup step.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

from config import DATA_DIR

_lock = threading.RLock()

FILES = {
    "users": "users.json",
    "clinics": "clinics.json",
    "health_tasks": "health_tasks.json",
    "task_submissions": "task_submissions.json",
    "messages": "messages.json",
    "appointments": "appointments.json",      # gap in the brief's file list - see docs
    "announcements": "announcements.json",    # same
    "outbox": "outbox.json",                  # dry-run email capture for demos/tests
}


def _path(name):
    if name not in FILES:
        raise KeyError(f"Unknown store '{name}' - add it to store.FILES first.")
    return Path(DATA_DIR) / FILES[name]


def load(name):
    """Return the dict in the named store, {} if the file doesn't exist yet."""
    with _lock:
        path = _path(name)
        if not path.exists():
            return {}
        with open(path, encoding="utf-8") as f:
            return json.load(f)


def save(name, data):
    """Atomically replace the named store's contents."""
    with _lock:
        path = _path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write next to the target so os.replace stays on one filesystem.
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise


def update(name, mutate):
    """
    Load-modify-save under the lock in one step.

        def add_user(record):
            def _apply(data):
                data[record["user_id"]] = record
            update("users", _apply)

    mutate() may return a value; update() passes it back to the caller.
    """
    with _lock:
        data = load(name)
        result = mutate(data)
        save(name, data)
        return result


def next_id(name, prefix):
    """Sequential ids like T001, A014 - readable in demos, stable in tests."""
    with _lock:
        data = load(name)
        numbers = [int(k[len(prefix):]) for k in data if k.startswith(prefix)
                   and k[len(prefix):].isdigit()]
        return f"{prefix}{(max(numbers) + 1) if numbers else 1:03d}"
