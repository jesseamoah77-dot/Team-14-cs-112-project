"""
Route-level security and workflow tests for ClinicCare-Lite, via the Flask test
client. This is where the rubric's access-control cases live: unauthenticated
access, wrong-role access, and - most importantly - patient A reaching for patient
B's records and getting a 404.

Run:  pytest tests/test_cliniccare_routes.py -v
"""

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "03-cliniccare-lite"))

import config  # noqa: E402


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "SUBMISSIONS_DIR", tmp_path / "submissions")
    monkeypatch.setattr(config, "SECRET_KEY", "test-secret")
    monkeypatch.setattr(config, "EMAIL_DRY_RUN", True)
    from models import store
    monkeypatch.setattr(store, "DATA_DIR", tmp_path / "data")
    import utils.file_handler as fh
    monkeypatch.setattr(fh, "SUBMISSIONS_DIR", tmp_path / "submissions")

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def population(app):
    """Doc + clinic + two patients, one task assigned to patient 1."""
    from models import clinic, health_task, user
    doc = user.register("12350000", "Dr Akosua Sarpong", "doc@example.com",
                        "Cl1nic!pass", "clinician")
    clinic_id = clinic.create("Adabraka Family Clinic", doc.user_id)
    doc.clinic_id = clinic_id
    doc.save()
    for pid, name in [("11112024", "Kojo Mensah"), ("22222025", "Abena Osei")]:
        p = user.register(pid, name, f"{pid}@example.com", "Pat1ent!aa",
                          "patient", clinic_id=clinic_id)
        clinic.add_patient(clinic_id, p.user_id)
    task_id = health_task.create(clinic_id, "BP log", "Weekly readings",
                                 "2030-01-01", ["11112024"],
                                 expected_fields=["Date", "Systolic"])
    return {"clinic_id": clinic_id, "task_id": task_id}


def login(client, user_id, password):
    return client.post("/login", data={"user_id": user_id, "password": password},
                       follow_redirects=False)


GOOD_CSV = b"Date,Systolic\n2026-07-01,120\n"


def submit_file(client, task_id, content=GOOD_CSV, name="log.csv"):
    return client.post(f"/patient/tasks/{task_id}/submit",
                       data={"file": (io.BytesIO(content), name)},
                       content_type="multipart/form-data")


# ---------------------------------------------------------------- authentication

class TestAuth:
    def test_login_routes_by_role(self, app, population):
        client = app.test_client()
        assert login(client, "12350000", "Cl1nic!pass").headers["Location"].endswith("/clinician/")
        client2 = app.test_client()
        assert login(client2, "11112024", "Pat1ent!aa").headers["Location"].endswith("/patient/")

    def test_bad_credentials_401(self, app, population):
        client = app.test_client()
        assert login(client, "12350000", "wrong").status_code == 401

    def test_registration_rejects_bad_id(self, app, population):
        client = app.test_client()
        response = client.post("/register", data={
            "role": "patient", "user_id": "12342030",  # 2030 outside 2022-2028
            "name": "X", "email": "x@example.com", "password": "Str0ng!pw",
            "clinic_id": population["clinic_id"]})
        assert response.status_code == 400

    def test_registration_rejects_weak_password(self, app, population):
        client = app.test_client()
        response = client.post("/register", data={
            "role": "patient", "user_id": "33332026", "name": "X",
            "email": "x@example.com", "password": "weakpass",
            "clinic_id": population["clinic_id"]})
        assert response.status_code == 400

    def test_logout_kills_session(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        client.get("/logout")
        assert client.get("/patient/").status_code == 302  # back to login


# ---------------------------------------------------------------- route protection

class TestRouteProtection:
    @pytest.mark.parametrize("url", ["/patient/", "/patient/inbox", "/patient/engagement",
                                     "/clinician/", "/clinician/submissions",
                                     "/clinician/analytics"])
    def test_unauthenticated_redirects_to_login(self, app, population, url):
        response = app.test_client().get(url)
        assert response.status_code == 302
        assert "/" in response.headers["Location"]

    def test_patient_cannot_open_clinician_pages(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        for url in ["/clinician/", "/clinician/submissions", "/clinician/analytics"]:
            assert client.get(url).status_code == 403, url

    def test_clinician_cannot_open_patient_pages(self, app, population):
        client = app.test_client()
        login(client, "12350000", "Cl1nic!pass")
        for url in ["/patient/", "/patient/engagement", "/patient/history"]:
            assert client.get(url).status_code == 403, url


# ---------------------------------------------------------------- submissions

class TestSubmission:
    def test_full_submit_and_review_workflow(self, app, population):
        task_id = population["task_id"]
        patient = app.test_client()
        login(patient, "11112024", "Pat1ent!aa")
        response = submit_file(patient, task_id)
        assert response.status_code == 302  # success -> dashboard

        # Clinician sees it, reviews it.
        doc = app.test_client()
        login(doc, "12350000", "Cl1nic!pass")
        key = f"11112024_{task_id}"
        assert doc.get(f"/clinician/submissions/{key}").status_code == 200
        response = doc.post(f"/clinician/submissions/{key}/review",
                            data={"outcome": "Reviewed - Normal", "notes": "All present."})
        assert response.status_code == 302

        # Patient's dashboard shows the outcome; inbox has the notification.
        page = patient.get("/patient/").data.decode()
        assert "Reviewed - Normal" in page
        inbox = patient.get("/patient/inbox").data.decode()
        assert "reviewed" in inbox.lower()

        # And the review email went to the outbox (dry-run).
        from models import store
        outbox = store.load("outbox")
        assert any("reviewed" in e["subject"].lower() for e in outbox.values())

    def test_incomplete_csv_rejected_with_reasons(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        response = submit_file(client, population["task_id"],
                               content=b"Date\n2026-07-01\n")
        assert response.status_code == 400
        assert b"Systolic" in response.data  # names the missing column

    def test_wrong_extension_rejected(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        response = submit_file(client, population["task_id"], name="log.exe",
                               content=b"MZ...")
        assert response.status_code == 400

    def test_unassigned_patient_gets_404(self, app, population):
        client = app.test_client()
        login(client, "22222025", "Pat1ent!aa")  # task not assigned to this patient
        assert client.get(f"/patient/tasks/{population['task_id']}/submit").status_code == 404

    def test_patient_cannot_fetch_other_patients_submission(self, app, population):
        task_id = population["task_id"]
        p1 = app.test_client()
        login(p1, "11112024", "Pat1ent!aa")
        submit_file(p1, task_id)

        p2 = app.test_client()
        login(p2, "22222025", "Pat1ent!aa")
        # 404, not 403: the system does not confirm the record exists.
        assert p2.get(f"/patient/submissions/11112024_{task_id}/download").status_code == 404

    def test_owner_can_download_own_file(self, app, population):
        task_id = population["task_id"]
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        submit_file(client, task_id)
        response = client.get(f"/patient/submissions/11112024_{task_id}/download")
        assert response.status_code == 200
        assert response.data == GOOD_CSV


# ---------------------------------------------------------------- messaging privacy

class TestMessagingRoutes:
    def test_thread_and_emergency_notice(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        page = client.get("/patient/messages")
        assert page.status_code == 200
        assert b"not monitored continuously" in page.data  # the required warning

        response = client.post("/patient/messages", data={"content": "Can I reschedule?"})
        assert response.status_code == 302

        doc = app.test_client()
        login(doc, "12350000", "Cl1nic!pass")
        thread = doc.get("/clinician/messages/11112024").data.decode()
        assert "Can I reschedule?" in thread

    def test_clinician_cannot_message_foreign_patient(self, app, population):
        from models import user as user_model
        # A patient of some other clinic entirely.
        user_model.register("99992027", "Stranger", "s@example.com", "Str0ng!pw1",
                            "patient", clinic_id=None)
        doc = app.test_client()
        login(doc, "12350000", "Cl1nic!pass")
        assert doc.get("/clinician/messages/99992027").status_code == 404

    def test_patient_inbox_shows_only_own_mail(self, app, population):
        from models import message
        message.notify("11112024", "For Kojo only")
        message.notify("22222025", "For Abena only")
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        page = client.get("/patient/inbox").data.decode()
        assert "For Kojo only" in page
        assert "For Abena only" not in page


# ---------------------------------------------------------------- engagement + analytics

class TestPrivacyPages:
    def test_engagement_private_and_own(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        submit_file(client, population["task_id"])  # earns on-time EP
        page = client.get("/patient/engagement").data.decode()
        assert "10" in page and "private to you" in page

    def test_analytics_page_never_names_patients(self, app, population):
        client = app.test_client()
        login(client, "11112024", "Pat1ent!aa")
        submit_file(client, population["task_id"])
        doc = app.test_client()
        login(doc, "12350000", "Cl1nic!pass")
        page = doc.get("/clinician/analytics").data.decode()
        # Aggregates only - no patient ids or names on the operational dashboard.
        assert "11112024" not in page
        assert "Kojo" not in page
