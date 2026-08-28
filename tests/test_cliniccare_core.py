"""
Tests for the ClinicCare-Lite model and utility layer (no Flask yet).

Every test runs against a temporary data directory - the real data/ folder is never
touched. That's done by pointing config.DATA_DIR/SUBMISSIONS_DIR at tmp_path before
the models import store state.

Run:  pytest tests/test_cliniccare_core.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03-cliniccare-lite"))

import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Point every store at a throwaway directory, fresh per test."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "SUBMISSIONS_DIR", tmp_path / "submissions")
    # store.py imported DATA_DIR by value, so patch it there too.
    from models import store
    monkeypatch.setattr(store, "DATA_DIR", tmp_path / "data")
    import utils.file_handler as fh
    monkeypatch.setattr(fh, "SUBMISSIONS_DIR", tmp_path / "submissions")
    yield


from models import (announcement, appointment, clinic, health_task, message,  # noqa: E402
                    store, task_submission, user)
from utils import analytics, completeness, engagement  # noqa: E402
from utils.validators import ValidationError, validate_password, validate_user_id  # noqa: E402


# ---------------------------------------------------------------- id + password rules

class TestValidators:
    def test_clinician_id_ok(self):
        assert validate_user_id("12350000", "clinician") == "12350000"

    @pytest.mark.parametrize("bad", ["1235000", "123500000", "12350001", "abcd0000", ""])
    def test_clinician_id_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_user_id(bad, "clinician")

    @pytest.mark.parametrize("good", ["12342022", "12342024", "12342028"])
    def test_patient_id_ok(self, good):
        assert validate_user_id(good, "patient") == good

    @pytest.mark.parametrize("bad", ["12342021", "12342029", "12340000", "1234202"])
    def test_patient_id_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_user_id(bad, "patient")

    def test_password_ok(self):
        validate_password("Str0ng!pass")

    @pytest.mark.parametrize("bad", [
        "alllowercase1!",  # no uppercase
        "ALLUPPERCASE1!",  # no lowercase
        "NoDigits!!",      # no digit
        "NoSpecial11a",    # no special
        "Sh0rt!a",         # 7 chars
    ])
    def test_password_bad(self, bad):
        with pytest.raises(ValidationError):
            validate_password(bad)

    def test_password_exactly_eight_with_all_classes_is_valid(self):
        validate_password("Short1!A")


# ---------------------------------------------------------------- store atomicity

class TestStore:
    def test_shrinking_write_leaves_no_trailing_bytes(self):
        # The exact bug the brief warns about: write big, then write small, re-read.
        store.save("users", {"k": "x" * 5000})
        store.save("users", {"k": "small"})
        assert store.load("users") == {"k": "small"}  # would raise "Extra data" if corrupt

    def test_sequential_ids(self):
        store.save("health_tasks", {})
        assert store.next_id("health_tasks", "T") == "T001"
        store.save("health_tasks", {"T001": {}, "T007": {}})
        assert store.next_id("health_tasks", "T") == "T008"


# ---------------------------------------------------------------- registration + login

@pytest.fixture()
def population():
    """A clinician with a clinic, and two patients registered to it."""
    doc = user.register("12350000", "Dr Akosua Sarpong", "doc@example.com",
                        "Cl1nic!pass", "clinician")
    clinic_id = clinic.create("Adabraka Family Clinic", doc.user_id)
    doc.clinic_id = clinic_id
    doc.save()
    p1 = user.register("11112024", "Kojo Mensah", "kojo@example.com",
                       "Pat1ent!aa", "patient", clinic_id=clinic_id)
    p2 = user.register("22222025", "Abena Osei", "abena@example.com",
                       "Pat1ent!bb", "patient", clinic_id=clinic_id)
    clinic.add_patient(clinic_id, p1.user_id)
    clinic.add_patient(clinic_id, p2.user_id)
    return {"doc": doc, "clinic_id": clinic_id, "p1": p1, "p2": p2}


class TestUsers:
    def test_register_and_login(self, population):
        u = user.authenticate("12350000", "Cl1nic!pass")
        assert u.role == "clinician"
        assert u.theme == "dark"  # spec: clinician default

    def test_patient_default_theme_colorful(self, population):
        assert user.get("11112024").theme == "colorful"

    def test_wrong_password(self, population):
        with pytest.raises(ValidationError):
            user.authenticate("12350000", "nope")

    def test_duplicate_id_rejected(self, population):
        with pytest.raises(ValidationError):
            user.register("12350000", "Imposter", "x@example.com", "Str0ng!pw1", "clinician")

    def test_password_hashed_at_rest(self, population):
        raw = store.load("users")["12350000"]["password"]
        assert "Cl1nic!pass" not in raw and raw.startswith("$2")

    def test_theme_switch(self, population):
        user.set_theme("11112024", "dark")
        assert user.get("11112024").theme == "dark"
        with pytest.raises(ValidationError):
            user.set_theme("11112024", "neon")


# ---------------------------------------------------------------- tasks + submissions

@pytest.fixture()
def task(population):
    task_id = health_task.create(
        population["clinic_id"], "BP log", "Submit your weekly readings",
        "2030-01-01", [population["p1"].user_id], expected_fields=["Date", "Systolic"])
    return task_id


class TestTasks:
    def test_create_and_query(self, population, task):
        assert task in health_task.for_clinic(population["clinic_id"])
        assert task in health_task.for_patient("11112024")
        assert task not in health_task.for_patient("22222025")

    def test_past_due_date_rejected(self, population):
        with pytest.raises(ValidationError):
            health_task.create(population["clinic_id"], "X", "Y", "2020-01-01", ["11112024"])

    def test_no_assignees_rejected(self, population):
        with pytest.raises(ValidationError):
            health_task.create(population["clinic_id"], "X", "Y", "2030-01-01", [])


class TestSubmissions:
    def test_record_and_review_flow(self, population, task):
        key = task_submission.record("11112024", task, "C001/11112024/11112024_T001.csv",
                                     {"complete": True, "problems": []})
        task_submission.review(key, "12350000", "Reviewed - Normal", "Looks complete.")
        sub = task_submission.get(key)
        assert sub["review"]["outcome"] == "Reviewed - Normal"
        assert sub["review"]["reviewer_id"] == "12350000"
        assert sub["review"]["reviewed_at"] is not None
        assert sub["review"]["patient_notified"] is False

    def test_unassigned_patient_cannot_submit(self, population, task):
        with pytest.raises(ValidationError):
            task_submission.record("22222025", task, "whatever.csv", {})

    def test_resubmission_before_review_allowed_and_flagged(self, population, task):
        task_submission.record("11112024", task, "a.csv", {})
        key = task_submission.record("11112024", task, "b.csv", {})
        assert task_submission.get(key)["resubmission"] is True

    def test_resubmission_after_review_blocked(self, population, task):
        key = task_submission.record("11112024", task, "a.csv", {})
        task_submission.review(key, "12350000", "Escalated")
        with pytest.raises(ValidationError):
            task_submission.record("11112024", task, "b.csv", {})

    def test_numeric_grade_is_not_a_valid_outcome(self, population, task):
        key = task_submission.record("11112024", task, "a.csv", {})
        with pytest.raises(ValidationError):
            task_submission.review(key, "12350000", "85")

    def test_clinic_filters(self, population, task):
        key = task_submission.record("11112024", task, "a.csv", {})
        assert key in task_submission.for_clinic(population["clinic_id"])
        assert key in task_submission.for_clinic(population["clinic_id"], outcome="Pending")
        assert not task_submission.for_clinic(population["clinic_id"], patient_id="22222025")


# ---------------------------------------------------------------- completeness checker

class TestCompleteness:
    def test_good_csv_passes(self):
        raw = b"Date,Systolic\n2026-07-01,120\n2026-07-02,118\n"
        result = completeness.check("log.csv", raw, ["Date", "Systolic"])
        assert result["complete"] is True

    def test_missing_column_reported(self):
        raw = b"Date\n2026-07-01\n"
        result = completeness.check("log.csv", raw, ["Date", "Systolic"])
        assert any("Systolic" in p for p in result["problems"])

    def test_empty_cells_reported(self):
        raw = b"Date,Systolic\n2026-07-01,\n"
        result = completeness.check("log.csv", raw, ["Date", "Systolic"])
        assert any("empty cells" in p for p in result["problems"])

    def test_non_date_flagged_structurally(self):
        raw = b"Date,Systolic\nyesterday,120\n"
        result = completeness.check("log.csv", raw, ["Date", "Systolic"])
        assert any("not dates" in p for p in result["problems"])

    def test_never_interprets_values(self):
        # A reading that would be alarming clinically - the checker must say nothing
        # beyond structure. This is the non-diagnostic boundary as a test.
        raw = b"Date,Systolic\n2026-07-01,240\n"
        result = completeness.check("log.csv", raw, ["Date", "Systolic"])
        assert result["complete"] is True
        assert result["problems"] == []

    def test_txt_field_lines(self):
        raw = b"Date: 2026-07-01\nNotes: slept well\n"
        result = completeness.check("diary.txt", raw, ["Date", "Notes"])
        assert result["complete"] is True
        missing = completeness.check("diary.txt", b"Notes: x\n", ["Date", "Notes"])
        assert any("Date" in p for p in missing["problems"])

    def test_pdf_skipped(self):
        result = completeness.check("scan.pdf", b"%PDF-1.4 ...", ["Date"])
        assert result["complete"] is True and "clinician" in result["note"]


# ---------------------------------------------------------------- messaging privacy

class TestMessaging:
    def test_conversation_is_pairwise_only(self, population):
        message.send("11112024", "12350000", "Can I move my appointment?")
        message.send("12350000", "11112024", "Yes - Thursday works.")
        message.send("22222025", "12350000", "Private question from Abena")

        p1_view = message.conversation("11112024", "12350000")
        assert len(p1_view) == 2
        assert all("Abena" not in m["content"] for m in p1_view)

        # Patient 1 asking for patient 2's conversation gets nothing - messages are
        # only returned for pairs the requester belongs to.
        assert message.conversation("11112024", "22222025") == []

    def test_inbox_and_unread(self, population):
        message.send("12350000", "11112024", "Reminder about your task")
        assert message.unread_count("11112024") == 1
        inbox = message.inbox("11112024")
        message.mark_read("11112024", inbox[0]["id"])
        assert message.unread_count("11112024") == 0

    def test_only_recipient_can_mark_read(self, population):
        mid = message.send("12350000", "11112024", "Hello")
        message.mark_read("22222025", mid)  # someone else - ignored
        assert message.unread_count("11112024") == 1

    def test_system_notifications_land_in_inbox(self, population):
        message.notify("11112024", "Your submission was received.")
        inbox = message.inbox("11112024")
        assert inbox[0]["kind"] == "notification"
        assert inbox[0]["sender_id"] == "SYSTEM"


# ---------------------------------------------------------------- appointments

class TestAppointments:
    def test_create_and_no_show(self, population):
        aid = appointment.create(population["clinic_id"], "11112024",
                                 "2030-06-01 09:30", "Quarterly review")
        appointment.set_status(aid, "No-show")
        assert appointment.for_patient("11112024")[aid]["status"] == "No-show"

    def test_past_time_rejected(self, population):
        with pytest.raises(ValidationError):
            appointment.create(population["clinic_id"], "11112024",
                               "2020-01-01 09:00", "X")

    def test_reminder_window(self, population, monkeypatch):
        from datetime import datetime, timedelta
        soon = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        far = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
        a_soon = appointment.create(population["clinic_id"], "11112024", soon, "Soon")
        appointment.create(population["clinic_id"], "11112024", far, "Far")
        due = appointment.due_for_reminder(within_hours=24)
        assert list(due) == [a_soon]
        appointment.mark_reminder_sent(a_soon)
        assert appointment.due_for_reminder(within_hours=24) == {}


# ---------------------------------------------------------------- announcements

class TestAnnouncements:
    def test_active_window_and_urgent_order(self, population):
        cid = population["clinic_id"]
        announcement.create(cid, "Holiday closure", "Closed Friday", urgent=False)
        announcement.create(cid, "Flu clinic", "Walk-ins this week", urgent=True)
        announcement.create(cid, "Old notice", "Expired", publish_date="2024-01-01",
                            expiry_date="2024-02-01")
        active = announcement.active_for_clinic(cid)
        assert [a["title"] for a in active] == ["Flu clinic", "Holiday closure"]
        assert len(announcement.all_for_clinic(cid)) == 3

    def test_expiry_before_publish_rejected(self, population):
        with pytest.raises(ValidationError):
            announcement.create(population["clinic_id"], "X", "Y",
                                publish_date="2030-01-10", expiry_date="2030-01-01")


# ---------------------------------------------------------------- engagement privacy

class TestEngagement:
    def test_on_time_awards_and_streak(self, population):
        engagement.on_submission("11112024", "2030-01-01", "2026-07-27 10:00:00")
        engagement.on_submission("11112024", "2030-01-01", "2026-07-27 11:00:00")
        s = engagement.summary("11112024")
        assert s["points"] == 20 and s["streak"] == 2

    def test_late_resets_streak_no_points(self, population):
        engagement.on_submission("11112024", "2030-01-01", "2026-07-27 10:00:00")
        engagement.on_submission("11112024", "2020-01-01", "2026-07-27 11:00:00")
        s = engagement.summary("11112024")
        assert s["points"] == 10 and s["streak"] == 0

    def test_attendance_points(self, population):
        engagement.on_attendance("11112024")
        assert engagement.summary("11112024")["points"] == 5

    def test_no_cross_patient_accessor_exists(self):
        # The privacy design as a test: the module must not offer any function that
        # reads engagement for anyone but the single requested patient.
        public = [n for n in dir(engagement) if not n.startswith("_")]
        assert "summary" in public
        assert not any("leaderboard" in n.lower() or "ranking" in n.lower()
                       or "compare" in n.lower() for n in public)


# ---------------------------------------------------------------- analytics scoping

class TestAnalytics:
    def test_clinic_summary_numbers(self, population):
        cid = population["clinic_id"]
        task_id = health_task.create(cid, "BP log", "Weekly", "2030-01-01",
                                     ["11112024", "22222025"])
        key = task_submission.record("11112024", task_id, "a.csv", {"complete": True})
        task_submission.review(key, "12350000", "Reviewed - Normal")

        summary = analytics.clinic_summary(cid)
        assert summary["assignments_expected"] == 2
        assert summary["submissions_received"] == 1
        assert summary["completion_rate_pct"] == 50.0
        assert summary["pending_reviews"] == 0
        assert summary["review_outcomes"] == {"Reviewed - Normal": 1}

    def test_patient_history_is_own_data_only(self, population):
        cid = population["clinic_id"]
        health_task.create(cid, "For both", "X", "2030-01-01", ["11112024", "22222025"])
        history = analytics.patient_history("11112024")
        assert history["tasks_assigned"] == 1
        # Nothing in the structure references the other patient.
        assert "22222025" not in str(history)
