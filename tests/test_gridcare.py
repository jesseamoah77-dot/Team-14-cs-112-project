"""
Tests for the GridCare-Lite logic layer (db, auth, services).

The GUI is a thin shell over these functions, so this is where the brief's test list
gets covered: invalid logins, role violations, bad substation references, illegal
status transitions, duplicates, missing fields. Each test uses a fresh in-memory
database - no files, no ordering dependencies.

Run:  pytest tests/test_gridcare.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "02-gridcare-lite"))

from gridcare import auth, db, services  # noqa: E402
from gridcare.validators import parse_date  # noqa: E402


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.init_db(connection)
    # Two substations to log outages against.
    connection.executemany(
        "INSERT INTO substations (substation_id, name, region, voltage_kv, capacity_mva, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "Tema Substation", "Greater Accra", 161, 250.0, "Active"),
            (2, "Tamale Substation", "Northern", 69, 45.0, "Active"),
        ],
    )
    connection.commit()
    return connection


@pytest.fixture()
def users(conn):
    """One user per role, returned as the dict rows the services expect."""
    made = {}
    for role in ("admin", "engineer", "technician", "customer_service"):
        auth.create_user(conn, role, "secret123", role.replace("_", " ").title(), role)
        made[role] = auth.authenticate(conn, role, "secret123")
    return made


# ---------------------------------------------------------------- auth

class TestAuth:
    def test_login_roundtrip(self, conn):
        auth.create_user(conn, "ama", "secret123", "Ama Mensah", "engineer")
        user = auth.authenticate(conn, "ama", "secret123")
        assert user["role"] == "engineer"

    def test_wrong_password_rejected(self, conn):
        auth.create_user(conn, "ama", "secret123", "Ama Mensah", "engineer")
        with pytest.raises(auth.AuthError):
            auth.authenticate(conn, "ama", "wrong")

    def test_unknown_user_same_error_as_wrong_password(self, conn):
        auth.create_user(conn, "ama", "secret123", "Ama Mensah", "engineer")
        try:
            auth.authenticate(conn, "ama", "wrong")
        except auth.AuthError as e:
            wrong_pw = str(e)
        try:
            auth.authenticate(conn, "nobody", "whatever")
        except auth.AuthError as e:
            unknown = str(e)
        # Identical message so the login screen doesn't leak which usernames exist.
        assert wrong_pw == unknown

    def test_password_is_hashed_at_rest(self, conn):
        auth.create_user(conn, "ama", "secret123", "Ama Mensah", "engineer")
        stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
        assert "secret123" not in stored
        assert stored.startswith("$2")  # bcrypt marker

    def test_duplicate_username_rejected(self, conn):
        auth.create_user(conn, "ama", "secret123", "Ama Mensah", "engineer")
        with pytest.raises(auth.AuthError):
            auth.create_user(conn, "ama", "other456", "Another Ama", "admin")

    def test_short_password_rejected(self, conn):
        with pytest.raises(auth.AuthError):
            auth.create_user(conn, "kofi", "abc", "Kofi Boateng", "technician")

    def test_invalid_role_rejected(self, conn):
        with pytest.raises(auth.AuthError):
            auth.create_user(conn, "kofi", "secret123", "Kofi Boateng", "manager")


# ---------------------------------------------------------------- outage logging

class TestOutages:
    def test_engineer_logs_outage(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Transformer trip", "High")
        rows = services.list_outages(conn, users["engineer"])
        assert rows[0]["outage_id"] == oid
        assert rows[0]["status"] == "Open"

    def test_technician_cannot_log_outage(self, conn, users):
        with pytest.raises(PermissionError):
            services.log_outage(conn, users["technician"], 1, "Trip", "Low")

    def test_customer_service_cannot_log_outage(self, conn, users):
        with pytest.raises(PermissionError):
            services.log_outage(conn, users["customer_service"], 1, "Trip", "Low")

    def test_nonexistent_substation_rejected(self, conn, users):
        with pytest.raises(services.ValidationError):
            services.log_outage(conn, users["engineer"], 999, "Trip", "Low")

    def test_blank_description_rejected(self, conn, users):
        with pytest.raises(services.ValidationError):
            services.log_outage(conn, users["engineer"], 1, "   ", "Low")

    def test_bad_severity_rejected(self, conn, users):
        with pytest.raises(services.ValidationError):
            services.log_outage(conn, users["engineer"], 1, "Trip", "Catastrophic")

    def test_duplicate_active_outage_flagged(self, conn, users):
        services.log_outage(conn, users["engineer"], 1, "Trip", "High")
        with pytest.raises(services.DuplicateOutageError):
            services.log_outage(conn, users["engineer"], 1, "Trip again", "Low")

    def test_duplicate_can_be_forced_after_confirmation(self, conn, users):
        services.log_outage(conn, users["engineer"], 1, "Trip", "High")
        oid = services.log_outage(conn, users["engineer"], 1, "Separate incident", "Low",
                                  allow_duplicate=True)
        assert oid is not None

    def test_status_history_written(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Trip", "High")
        history = services.get_history(conn, "outage", oid)
        assert len(history) == 1
        assert history[0]["new_status"] == "Open"


# ---------------------------------------------------------------- the full workflow

def full_workflow(conn, users):
    """Drive the brief's demo sequence end to end; returns (outage_id, work_order_id)."""
    oid = services.log_outage(conn, users["engineer"], 1, "Feeder fault", "Critical")
    wid = services.create_work_order(conn, users["admin"], oid)
    services.assign_work_order(conn, users["admin"], wid,
                               users["technician"]["user_id"], "2030-01-15")
    services.start_work(conn, users["technician"], wid)
    services.complete_work(conn, users["technician"], wid, "Replaced blown fuse, retested feeder.")
    return oid, wid


class TestWorkflow:
    def test_outage_to_resolution(self, conn, users):
        oid, wid = full_workflow(conn, users)
        outage = conn.execute("SELECT * FROM outages WHERE outage_id = ?", (oid,)).fetchone()
        wo = conn.execute("SELECT * FROM work_orders WHERE work_order_id = ?", (wid,)).fetchone()
        assert outage["status"] == "Resolved" and outage["resolved_at"] is not None
        assert wo["status"] == "Completed" and wo["work_notes"]

    def test_full_history_trail(self, conn, users):
        oid, wid = full_workflow(conn, users)
        outage_states = [h["new_status"] for h in services.get_history(conn, "outage", oid)]
        wo_states = [h["new_status"] for h in services.get_history(conn, "work_order", wid)]
        assert outage_states == ["Open", "In Progress", "Resolved"]
        assert wo_states == ["Pending", "Scheduled", "Completed"]

    def test_engineer_cannot_create_work_order(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        with pytest.raises(PermissionError):
            services.create_work_order(conn, users["engineer"], oid)

    def test_second_open_work_order_blocked(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        services.create_work_order(conn, users["admin"], oid)
        with pytest.raises(services.ValidationError):
            services.create_work_order(conn, users["admin"], oid)

    def test_assign_requires_technician_role(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        with pytest.raises(services.ValidationError):
            services.assign_work_order(conn, users["admin"], wid,
                                       users["engineer"]["user_id"], "2030-01-15")

    def test_past_scheduled_date_rejected(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        with pytest.raises(services.ValidationError):
            services.assign_work_order(conn, users["admin"], wid,
                                       users["technician"]["user_id"], "2020-01-01")

    def test_garbage_date_rejected(self, conn, users):
        with pytest.raises(services.ValidationError):
            parse_date("2026-13-45")
        with pytest.raises(services.ValidationError):
            parse_date("next tuesday")

    def test_cannot_start_unscheduled_order(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        with pytest.raises(services.ValidationError):
            services.start_work(conn, users["technician"], wid)  # still Pending

    def test_wrong_technician_blocked(self, conn, users):
        auth.create_user(conn, "tech2", "secret123", "Second Tech", "technician")
        other = auth.authenticate(conn, "tech2", "secret123")
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        services.assign_work_order(conn, users["admin"], wid,
                                   users["technician"]["user_id"], "2030-01-15")
        with pytest.raises(PermissionError):
            services.start_work(conn, other, wid)

    def test_completion_requires_notes(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        services.assign_work_order(conn, users["admin"], wid,
                                   users["technician"]["user_id"], "2030-01-15")
        services.start_work(conn, users["technician"], wid)
        with pytest.raises(services.ValidationError):
            services.complete_work(conn, users["technician"], wid, "")

    def test_resolved_is_final(self, conn, users):
        oid, wid = full_workflow(conn, users)
        with pytest.raises(services.ValidationError):
            services.create_work_order(conn, users["admin"], oid)  # resolved outage

    def test_technician_sees_only_own_orders(self, conn, users):
        auth.create_user(conn, "tech2", "secret123", "Second Tech", "technician")
        other = auth.authenticate(conn, "tech2", "secret123")
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        wid = services.create_work_order(conn, users["admin"], oid)
        services.assign_work_order(conn, users["admin"], wid,
                                   users["technician"]["user_id"], "2030-01-15")
        assert len(services.list_work_orders(conn, users["technician"])) == 1
        assert len(services.list_work_orders(conn, other)) == 0


# ---------------------------------------------------------------- complaints

class TestComplaints:
    def test_log_and_link(self, conn, users):
        oid = services.log_outage(conn, users["engineer"], 1, "Fault", "High")
        cid = services.log_complaint(conn, users["customer_service"],
                                     "Kwame Asante", "No power since morning", outage_id=oid)
        rows = services.list_complaints(conn, users["customer_service"])
        assert rows[0]["complaint_id"] == cid
        assert rows[0]["outage_id"] == oid
        assert rows[0]["substation"] == "Tema Substation"

    def test_link_to_missing_outage_rejected(self, conn, users):
        with pytest.raises(services.ValidationError):
            services.log_complaint(conn, users["customer_service"],
                                   "Kwame Asante", "No power", outage_id=424242)

    def test_unlinked_complaint_fine(self, conn, users):
        cid = services.log_complaint(conn, users["customer_service"],
                                     "Ama Serwaa", "Flickering supply")
        assert cid is not None

    def test_engineer_cannot_log_complaint(self, conn, users):
        with pytest.raises(PermissionError):
            services.log_complaint(conn, users["engineer"], "Someone", "Something")


# ---------------------------------------------------------------- reports

class TestReports:
    def test_summary_counts(self, conn, users):
        full_workflow(conn, users)                                         # 1 resolved
        services.log_outage(conn, users["engineer"], 2, "New fault", "Medium")  # 1 open
        services.log_complaint(conn, users["customer_service"], "K. Asante", "No power")

        summary = services.report_summary(conn, users["admin"])
        assert summary["by_status"] == {"Resolved": 1, "Open": 1}
        assert summary["open_by_severity"] == {"Medium": 1}
        assert summary["open_by_region"] == [("Northern", 1)]
        assert summary["complaints_total"] == 1
        assert summary["complaints_linked"] == 0
        # Same-second resolution in the test, so hours is ~0 - but present, not None.
        assert summary["avg_resolution_hours"] is not None

    def test_no_resolved_outages_gives_none_average(self, conn, users):
        services.log_outage(conn, users["engineer"], 1, "Fault", "Low")
        summary = services.report_summary(conn, users["admin"])
        assert summary["avg_resolution_hours"] is None


# ---------------------------------------------------------------- reference import

class TestImport:
    def test_import_real_cleaned_csvs(self, conn):
        data_dir = Path(__file__).resolve().parent.parent / "01-grid-analysis" / "data"
        subs = data_dir / "clean_substations.csv"
        lines = data_dir / "clean_lines.csv"
        if not subs.exists():
            pytest.skip("run the grid-analysis cleaning notebook first")
        # The fixture pre-seeded ids 1 and 2; INSERT OR REPLACE makes import idempotent.
        n_subs = db.import_substations(conn, subs)
        n_lines = db.import_lines(conn, lines)
        assert n_subs == 44
        assert n_lines == 55
        # Re-import must not duplicate.
        db.import_substations(conn, subs)
        count = conn.execute("SELECT COUNT(*) FROM substations").fetchone()[0]
        assert count == 44
