"""
Database layer for GridCare-Lite.

SQLite, one file per installation (data/gridcare.db by default). Schema notes:

- Roles and statuses are CHECK-constrained in the schema, not just validated in the
  UI - the brief is explicit that role separation must live in application logic and
  database rules, "not merely by hiding buttons".
- status_history records every outage/work-order transition with who and when. The
  reports screen reads resolution times from the outage timestamps, and the history
  table is the audit trail the demo can show.
- substations/lines are reference data imported from the cleaned CSVs produced by the
  grid-analysis component, so an outage can only ever be logged against a real asset
  (enforced by the foreign key).
"""

import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "gridcare.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'engineer', 'technician', 'customer_service'))
);

CREATE TABLE IF NOT EXISTS substations (
    substation_id INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    region        TEXT NOT NULL,
    voltage_kv    INTEGER,
    capacity_mva  REAL,
    status        TEXT
);

CREATE TABLE IF NOT EXISTS lines (
    line_id                    INTEGER PRIMARY KEY,
    utility_code               TEXT,
    source_substation_id       INTEGER NOT NULL REFERENCES substations(substation_id),
    destination_substation_id  INTEGER NOT NULL REFERENCES substations(substation_id),
    voltage_kv                 INTEGER,
    length_km                  REAL,
    status                     TEXT
);

CREATE TABLE IF NOT EXISTS outages (
    outage_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    substation_id INTEGER NOT NULL REFERENCES substations(substation_id),
    reported_by   INTEGER NOT NULL REFERENCES users(user_id),
    description   TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    status        TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open', 'In Progress', 'Resolved')),
    reported_at   TEXT NOT NULL,
    resolved_at   TEXT
);

CREATE TABLE IF NOT EXISTS work_orders (
    work_order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    outage_id           INTEGER NOT NULL REFERENCES outages(outage_id),
    created_by          INTEGER NOT NULL REFERENCES users(user_id),
    assigned_technician INTEGER REFERENCES users(user_id),
    scheduled_date      TEXT,
    status              TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Scheduled', 'Completed')),
    work_notes          TEXT,
    created_at          TEXT NOT NULL,
    completed_at        TEXT
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_by     INTEGER NOT NULL REFERENCES users(user_id),
    customer_name TEXT NOT NULL,
    contact       TEXT,
    description   TEXT NOT NULL,
    outage_id     INTEGER REFERENCES outages(outage_id),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS status_history (
    history_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('outage', 'work_order')),
    entity_id   INTEGER NOT NULL,
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    changed_by  INTEGER NOT NULL REFERENCES users(user_id),
    changed_at  TEXT NOT NULL,
    note        TEXT
);

CREATE INDEX IF NOT EXISTS idx_outages_substation ON outages(substation_id, status);
CREATE INDEX IF NOT EXISTS idx_work_orders_technician ON work_orders(assigned_technician, status);
"""


def connect(db_path=DEFAULT_DB):
    """Open a connection with foreign keys on and dict-style row access."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Foreign keys are per-connection in SQLite and OFF by default. Without this,
    # every REFERENCES clause in the schema is decoration.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def import_substations(conn, csv_path):
    """
    Load the cleaned substations CSV from the grid-analysis component.

    Re-running is safe: INSERT OR REPLACE keyed on the substation id, so a re-import
    updates rather than duplicates. Returns the number of rows imported.
    """
    import csv

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = [
            (
                int(r["Substation ID"]),
                r["Name"],
                r["Region"],
                int(float(r["Voltage (kV)"])),
                float(r["Capacity (MVA)"]),
                r["Status"],
            )
            for r in csv.DictReader(f)
        ]
    conn.executemany(
        "INSERT OR REPLACE INTO substations "
        "(substation_id, name, region, voltage_kv, capacity_mva, status) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def import_lines(conn, csv_path):
    """Same idea as import_substations, for the lines reference table."""
    import csv

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = [
            (
                int(r["Line ID"]),
                r.get("Code", ""),
                int(r["Source Substation ID"]),
                int(r["Destination Substation ID"]),
                int(float(r["Voltage (kV)"])),
                float(r["Length (km)"]),
                r["Status"],
            )
            for r in csv.DictReader(f)
        ]
    conn.executemany(
        "INSERT OR REPLACE INTO lines "
        "(line_id, utility_code, source_substation_id, destination_substation_id, "
        "voltage_kv, length_km, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)
