"""
Business logic for GridCare-Lite.

Every operation the GUI can perform goes through a function here, and every function
checks the caller's role itself. The screens also hide controls a role shouldn't see,
but that is cosmetics - this module is the enforcement. A technician calling
create_work_order() gets PermissionError no matter what the UI showed them.

Status transitions are defined once in the *_TRANSITIONS tables below and checked on
every change, so an outage can never jump Open -> Resolved without going through a
completed work order, and nothing can un-resolve.
"""

from .auth import now_iso

SEVERITIES = ("Low", "Medium", "High", "Critical")

# state -> the states it may legally move to
OUTAGE_TRANSITIONS = {
    "Open": {"In Progress"},
    "In Progress": {"Resolved"},
    "Resolved": set(),
}
WORK_ORDER_TRANSITIONS = {
    "Pending": {"Scheduled"},
    "Scheduled": {"Completed"},
    "Completed": set(),
}


class ValidationError(Exception):
    """User input problem. Message is written to be shown directly in the UI."""


class DuplicateOutageError(ValidationError):
    """The substation already has an unresolved outage. UI asks before proceeding."""


def _require_role(user, *allowed):
    if user["role"] not in allowed:
        raise PermissionError(
            f"Role '{user['role']}' is not permitted to do this (needs: {', '.join(allowed)})."
        )


def _record_status(conn, entity_type, entity_id, old, new, user, note=None):
    conn.execute(
        "INSERT INTO status_history (entity_type, entity_id, old_status, new_status, "
        "changed_by, changed_at, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (entity_type, entity_id, old, new, user["user_id"], now_iso(), note),
    )


def _check_transition(table, current, new):
    allowed = table.get(current, set())
    if new not in allowed:
        raise ValidationError(
            f"Cannot move from '{current}' to '{new}'"
            + (f" (allowed: {', '.join(sorted(allowed))})." if allowed else " - it is final.")
        )


# ---------------------------------------------------------------- outages

def log_outage(conn, user, substation_id, description, severity, allow_duplicate=False):
    """
    Engineer (or admin) records a new outage against a substation.

    If the substation already has an unresolved outage, DuplicateOutageError is raised
    so the UI can ask "are you sure this is a separate incident?" - a second report of
    the same fault is the most likely duplicate-entry mistake in this workflow.
    """
    _require_role(user, "engineer", "admin")

    description = (description or "").strip()
    if not description:
        raise ValidationError("Description is required.")
    if severity not in SEVERITIES:
        raise ValidationError(f"Severity must be one of: {', '.join(SEVERITIES)}.")

    sub = conn.execute(
        "SELECT substation_id, name FROM substations WHERE substation_id = ?", (substation_id,)
    ).fetchone()
    if sub is None:
        raise ValidationError(f"Substation id {substation_id} does not exist.")

    if not allow_duplicate:
        active = conn.execute(
            "SELECT outage_id FROM outages WHERE substation_id = ? AND status != 'Resolved'",
            (substation_id,),
        ).fetchone()
        if active:
            raise DuplicateOutageError(
                f"{sub['name']} already has unresolved outage #{active['outage_id']}. "
                "Log this as a separate incident anyway?"
            )

    cur = conn.execute(
        "INSERT INTO outages (substation_id, reported_by, description, severity, status, reported_at) "
        "VALUES (?, ?, ?, ?, 'Open', ?)",
        (substation_id, user["user_id"], description, severity, now_iso()),
    )
    _record_status(conn, "outage", cur.lastrowid, None, "Open", user, "Outage reported")
    conn.commit()
    return cur.lastrowid


def list_outages(conn, user, status=None, region=None):
    """Any authenticated staff role can view outages; filters are optional."""
    _require_role(user, "admin", "engineer", "technician", "customer_service")
    sql = """
        SELECT o.outage_id, s.name AS substation, s.region, o.description, o.severity,
               o.status, o.reported_at, o.resolved_at, u.full_name AS reported_by
        FROM outages o
        JOIN substations s ON s.substation_id = o.substation_id
        JOIN users u ON u.user_id = o.reported_by
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND o.status = ?"
        params.append(status)
    if region:
        sql += " AND s.region = ?"
        params.append(region)
    sql += " ORDER BY o.reported_at DESC"
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------- work orders

def create_work_order(conn, user, outage_id):
    """Admin creates a work order for an open outage. Starts as Pending."""
    _require_role(user, "admin")

    outage = conn.execute("SELECT * FROM outages WHERE outage_id = ?", (outage_id,)).fetchone()
    if outage is None:
        raise ValidationError(f"Outage #{outage_id} does not exist.")
    if outage["status"] == "Resolved":
        raise ValidationError("That outage is already resolved.")

    existing = conn.execute(
        "SELECT work_order_id FROM work_orders WHERE outage_id = ? AND status != 'Completed'",
        (outage_id,),
    ).fetchone()
    if existing:
        raise ValidationError(f"Outage #{outage_id} already has open work order #{existing['work_order_id']}.")

    cur = conn.execute(
        "INSERT INTO work_orders (outage_id, created_by, status, created_at) VALUES (?, ?, 'Pending', ?)",
        (outage_id, user["user_id"], now_iso()),
    )
    _record_status(conn, "work_order", cur.lastrowid, None, "Pending", user, "Work order created")
    conn.commit()
    return cur.lastrowid


def assign_work_order(conn, user, work_order_id, technician_id, scheduled_date):
    """Admin assigns a technician and date -> Pending becomes Scheduled."""
    from .validators import parse_date

    _require_role(user, "admin")

    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (work_order_id,)).fetchone()
    if wo is None:
        raise ValidationError(f"Work order #{work_order_id} does not exist.")
    _check_transition(WORK_ORDER_TRANSITIONS, wo["status"], "Scheduled")

    tech = conn.execute(
        "SELECT user_id, role FROM users WHERE user_id = ?", (technician_id,)
    ).fetchone()
    if tech is None or tech["role"] != "technician":
        raise ValidationError("Assignee must be an existing user with the technician role.")

    scheduled = parse_date(scheduled_date, allow_past=False)

    conn.execute(
        "UPDATE work_orders SET assigned_technician = ?, scheduled_date = ?, status = 'Scheduled' "
        "WHERE work_order_id = ?",
        (technician_id, scheduled, work_order_id),
    )
    _record_status(conn, "work_order", work_order_id, "Pending", "Scheduled", user,
                   f"Assigned technician {technician_id} for {scheduled}")
    conn.commit()


def start_work(conn, user, work_order_id):
    """Assigned technician starts the job -> the outage moves Open -> In Progress."""
    _require_role(user, "technician", "admin")

    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (work_order_id,)).fetchone()
    if wo is None:
        raise ValidationError(f"Work order #{work_order_id} does not exist.")
    # Status before ownership: a Pending order has no assignee yet, and "assigned to a
    # different technician" would be a misleading message for it.
    if wo["status"] != "Scheduled":
        raise ValidationError(f"Work order is '{wo['status']}' - only a Scheduled order can be started.")
    if user["role"] == "technician" and wo["assigned_technician"] != user["user_id"]:
        raise PermissionError("That work order is assigned to a different technician.")

    outage = conn.execute("SELECT * FROM outages WHERE outage_id = ?", (wo["outage_id"],)).fetchone()
    _check_transition(OUTAGE_TRANSITIONS, outage["status"], "In Progress")

    conn.execute("UPDATE outages SET status = 'In Progress' WHERE outage_id = ?", (outage["outage_id"],))
    _record_status(conn, "outage", outage["outage_id"], "Open", "In Progress", user,
                   f"Work started on WO #{work_order_id}")
    conn.commit()


def complete_work(conn, user, work_order_id, work_notes):
    """
    Assigned technician records what was done and closes out the job.

    Completing the work order also resolves its outage - one action, both records,
    so the pair can never disagree about whether the fault is fixed.
    """
    _require_role(user, "technician", "admin")

    wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (work_order_id,)).fetchone()
    if wo is None:
        raise ValidationError(f"Work order #{work_order_id} does not exist.")
    if user["role"] == "technician" and wo["assigned_technician"] != user["user_id"]:
        raise PermissionError("That work order is assigned to a different technician.")
    _check_transition(WORK_ORDER_TRANSITIONS, wo["status"], "Completed")

    if not (work_notes or "").strip():
        raise ValidationError("Work notes are required - record what was actually done.")

    outage = conn.execute("SELECT * FROM outages WHERE outage_id = ?", (wo["outage_id"],)).fetchone()
    _check_transition(OUTAGE_TRANSITIONS, outage["status"], "Resolved")

    stamp = now_iso()
    conn.execute(
        "UPDATE work_orders SET status = 'Completed', work_notes = ?, completed_at = ? "
        "WHERE work_order_id = ?",
        (work_notes.strip(), stamp, work_order_id),
    )
    conn.execute(
        "UPDATE outages SET status = 'Resolved', resolved_at = ? WHERE outage_id = ?",
        (stamp, outage["outage_id"]),
    )
    _record_status(conn, "work_order", work_order_id, wo["status"], "Completed", user, "Work completed")
    _record_status(conn, "outage", outage["outage_id"], outage["status"], "Resolved", user,
                   f"Resolved via WO #{work_order_id}")
    conn.commit()


def list_work_orders(conn, user, technician_id=None):
    """Technicians see their own orders; admin/engineer can see all."""
    _require_role(user, "admin", "engineer", "technician")
    if user["role"] == "technician":
        technician_id = user["user_id"]  # technicians cannot browse other people's queues

    sql = """
        SELECT w.work_order_id, w.outage_id, s.name AS substation, s.region,
               o.severity, w.status, w.scheduled_date, w.work_notes,
               t.full_name AS technician, w.created_at, w.completed_at
        FROM work_orders w
        JOIN outages o ON o.outage_id = w.outage_id
        JOIN substations s ON s.substation_id = o.substation_id
        LEFT JOIN users t ON t.user_id = w.assigned_technician
    """
    params = []
    if technician_id is not None:
        sql += " WHERE w.assigned_technician = ?"
        params.append(technician_id)
    sql += " ORDER BY w.created_at DESC"
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------- complaints

def log_complaint(conn, user, customer_name, description, contact=None, outage_id=None):
    """Customer service records a complaint, optionally linked to a known outage."""
    _require_role(user, "customer_service", "admin")

    if not (customer_name or "").strip():
        raise ValidationError("Customer name is required.")
    if not (description or "").strip():
        raise ValidationError("Complaint description is required.")
    if outage_id is not None:
        outage = conn.execute("SELECT 1 FROM outages WHERE outage_id = ?", (outage_id,)).fetchone()
        if outage is None:
            raise ValidationError(f"Cannot link: outage #{outage_id} does not exist.")

    cur = conn.execute(
        "INSERT INTO complaints (logged_by, customer_name, contact, description, outage_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user["user_id"], customer_name.strip(), (contact or "").strip() or None,
         description.strip(), outage_id, now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def list_complaints(conn, user):
    _require_role(user, "customer_service", "admin", "engineer")
    return conn.execute("""
        SELECT c.complaint_id, c.customer_name, c.contact, c.description,
               c.outage_id, s.name AS substation, c.created_at, u.full_name AS logged_by
        FROM complaints c
        LEFT JOIN outages o ON o.outage_id = c.outage_id
        LEFT JOIN substations s ON s.substation_id = o.substation_id
        JOIN users u ON u.user_id = c.logged_by
        ORDER BY c.created_at DESC
    """).fetchall()


# ---------------------------------------------------------------- reference + reports

def list_substations(conn):
    """Reference data for pickers - no role gate, every screen needs it."""
    return conn.execute(
        "SELECT substation_id, name, region, voltage_kv, status FROM substations ORDER BY name"
    ).fetchall()


def list_technicians(conn):
    return conn.execute(
        "SELECT user_id, full_name FROM users WHERE role = 'technician' ORDER BY full_name"
    ).fetchall()


def get_history(conn, entity_type, entity_id):
    return conn.execute("""
        SELECT h.changed_at, h.old_status, h.new_status, h.note, u.full_name AS changed_by
        FROM status_history h JOIN users u ON u.user_id = h.changed_by
        WHERE h.entity_type = ? AND h.entity_id = ?
        ORDER BY h.changed_at
    """, (entity_type, entity_id)).fetchall()


def report_summary(conn, user):
    """The numbers behind the reports screen, in one round trip per figure."""
    _require_role(user, "admin", "engineer", "customer_service", "technician")

    by_status = dict(conn.execute(
        "SELECT status, COUNT(*) FROM outages GROUP BY status").fetchall())
    by_severity = dict(conn.execute(
        "SELECT severity, COUNT(*) FROM outages WHERE status != 'Resolved' GROUP BY severity").fetchall())
    by_region = conn.execute("""
        SELECT s.region, COUNT(*) AS n
        FROM outages o JOIN substations s ON s.substation_id = o.substation_id
        WHERE o.status != 'Resolved'
        GROUP BY s.region ORDER BY n DESC
    """).fetchall()

    # Average hours from report to resolution. julianday() gives fractional days,
    # so x24 makes hours; only resolved outages have both timestamps.
    avg_hours = conn.execute("""
        SELECT AVG((julianday(resolved_at) - julianday(reported_at)) * 24.0)
        FROM outages WHERE resolved_at IS NOT NULL
    """).fetchone()[0]

    linked = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE outage_id IS NOT NULL").fetchone()[0]
    total_complaints = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]

    return {
        "by_status": by_status,
        "open_by_severity": by_severity,
        "open_by_region": [(r["region"], r["n"]) for r in by_region],
        "avg_resolution_hours": round(avg_hours, 1) if avg_hours is not None else None,
        "complaints_total": total_complaints,
        "complaints_linked": linked,
    }
