"""
Clinics tie one clinician to their registered patients.

The registration flow the spec implies but doesn't spell out, made concrete here:
a clinic is created automatically when a clinician registers (named from the form),
and patients pick an existing clinic when they register. Every access-control
question later ("may this clinician see this submission?") reduces to membership in
this file.

    { "C001": {"name": "...", "clinician_id": "12350000", "patient_ids": [...] } }
"""

from models import store
from utils.validators import ValidationError, require


def create(name, clinician_id):
    name = require(name, "Clinic name")

    def _apply(data):
        clinic_id = store.next_id("clinics", "C")
        data[clinic_id] = {"name": name, "clinician_id": clinician_id, "patient_ids": []}
        return clinic_id
    return store.update("clinics", _apply)


def add_patient(clinic_id, patient_id):
    def _apply(data):
        if clinic_id not in data:
            raise ValidationError(f"Clinic {clinic_id} does not exist.")
        if patient_id not in data[clinic_id]["patient_ids"]:
            data[clinic_id]["patient_ids"].append(patient_id)
    store.update("clinics", _apply)


def get(clinic_id):
    return store.load("clinics").get(clinic_id)


def list_all():
    return store.load("clinics")


def for_clinician(clinician_id):
    """The clinic this clinician runs, or None. One clinic per clinician by design."""
    for clinic_id, record in store.load("clinics").items():
        if record["clinician_id"] == clinician_id:
            return clinic_id, record
    return None, None


def patient_in_clinic(clinic_id, patient_id):
    record = get(clinic_id)
    return bool(record) and patient_id in record["patient_ids"]
