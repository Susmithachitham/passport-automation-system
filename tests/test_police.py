import os
import unittest
from datetime import date, time

from app import create_app
from backend.extensions import db
from backend.models import Application, Document, Interview, Payment, PoliceVerification, User


class PoliceWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "UPLOAD_FOLDER": os.path.join(os.getcwd(), "uploads", "documents", "test"),
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.applicant = self._user("Applicant", "applicant@example.com", "applicant")
        self.officer = self._user("Officer", "officer@example.com", "officer")
        self.police = self._user("Police", "police@example.com", "police")
        db.session.add_all([self.applicant, self.officer, self.police])
        db.session.flush()
        self.application = Application(
            application_id="PSP202600000002",
            applicant_id=self.applicant.id,
            application_type="NEW",
            status="POLICE_VERIFICATION",
            personal_details={"full_name": "Applicant", "date_of_birth": "2000-01-12", "gender": "Male", "place_of_birth": "Delhi", "nationality": "Indian", "mobile_number": "+91 9876543210", "email": "applicant@example.com", "father_name": "Father", "mother_name": "Mother"},
            address_details={"current_address": {"city": "Delhi"}, "permanent_address": {"city": "Delhi"}},
            family_details={"father_name": "Father", "mother_name": "Mother"},
            passport_details={"previous_passport_held": "No"},
        )
        db.session.add(self.application)
        db.session.flush()
        for document_type in ("Identity Proof", "Address Proof", "Date of Birth Proof", "Photograph", "Signature"):
            db.session.add(Document(application_id=self.application.id, document_type=document_type, original_filename=f"{document_type}.pdf", stored_filename=f"{document_type}.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf", file_size=100, verification_status="VERIFIED", verification_remarks="Officer verified"))
        db.session.add(Payment(application_id=self.application.id, transaction_id="TXN-2026-POLICE01", amount=1500, payment_method="UPI", payment_status="SUCCESS"))
        db.session.add(Interview(application_id=self.application.id, officer_id=self.officer.id, scheduled_date=date(2026, 9, 20), scheduled_time=time(10, 30), location="Passport Office", status="COMPLETED", officer_remarks="Completed"))
        db.session.commit()
        self.application_id = self.application.application_id

    @staticmethod
    def _user(name, email, role):
        user = User(full_name=name, email=email, password_hash="", phone="+1 555 123 4567", address="Test address", role=role)
        user.set_password("Password@123")
        return user

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, role="police"):
        email = {"applicant": "applicant@example.com", "officer": "officer@example.com", "police": "police@example.com"}[role]
        return self.client.post("/api/auth/login", json={"email": email, "password": "Password@123"})

    def verification_payload(self, result="CLEAR", remarks="Verification completed successfully."):
        return {"verification_status": result, "address_verified": True, "identity_verified": True, "applicant_found": True, "criminal_record_found": False, "remarks": remarks}

    def test_unauthenticated_police_api_is_denied(self):
        self.assertEqual(self.client.get("/api/police/dashboard").status_code, 401)

    def test_applicant_cannot_access_police_dashboard_or_submit(self):
        self.login("applicant")
        self.assertEqual(self.client.get("/api/police/dashboard").status_code, 403)
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload()).status_code, 403)

    def test_officer_cannot_use_police_verification_api(self):
        self.login("officer")
        self.assertEqual(self.client.get("/api/police/applications").status_code, 403)
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload()).status_code, 403)

    def test_police_dashboard_uses_database_statistics(self):
        self.login()
        response = self.client.get("/api/police/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["pending_verification"], 1)
        self.assertEqual(response.json["data"]["total_cases"], 1)

    def test_police_can_search_filter_and_paginate_queue(self):
        self.login()
        response = self.client.get(f"/api/police/applications?search=Applicant&sort=oldest&page=1&per_page=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["items"][0]["application_id"], self.application_id)
        self.assertEqual(response.json["data"]["per_page"], 1)

    def test_police_can_view_eligible_application_and_verification(self):
        self.login()
        detail = self.client.get(f"/api/police/applications/{self.application_id}")
        verification = self.client.get(f"/api/police/applications/{self.application_id}/verification")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["data"]["applicant"]["email"], "applicant@example.com")
        self.assertEqual(len(detail.json["data"]["documents"]), 5)
        self.assertEqual(detail.json["data"]["interview"]["status"], "COMPLETED")
        self.assertEqual(verification.json["data"]["verification_status"], "PENDING")

    def test_non_eligible_application_is_not_visible_or_modifiable(self):
        self.login()
        self.application.status = "SUBMITTED"
        db.session.commit()
        self.assertEqual(self.client.get(f"/api/police/applications/{self.application_id}").status_code, 409)
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload()).status_code, 409)

    def test_police_cannot_change_or_delete_documents(self):
        self.login()
        document_id = self.application.documents[0].id
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/documents/{document_id}/verify").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/police/applications/{self.application_id}/documents/{document_id}").status_code, 404)
        self.assertEqual(db.session.get(Document, document_id).verification_status, "VERIFIED")

    def test_invalid_verification_status_and_incomplete_fields_are_rejected(self):
        self.login()
        invalid = self.verification_payload()
        invalid["verification_status"] = "APPROVED"
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=invalid).status_code, 400)
        incomplete = self.verification_payload()
        incomplete["identity_verified"] = None
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=incomplete).status_code, 400)

    def test_clear_requires_complete_verification(self):
        self.login()
        payload = self.verification_payload()
        payload["applicant_found"] = False
        response = self.client.post(f"/api/police/applications/{self.application_id}/verification", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_clear_changes_application_to_approved_and_records_audit(self):
        self.login()
        response = self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["data"]["verification_status"], "CLEAR")
        record = db.session.get(PoliceVerification, response.json["data"]["id"])
        self.assertEqual(record.police_officer_id, self.police.id)
        self.assertIsNotNone(record.verification_date)
        self.assertEqual(db.session.get(Application, self.application.id).status, "APPROVED")

    def test_not_clear_requires_remarks(self):
        self.login()
        payload = self.verification_payload("NOT_CLEAR", "")
        response = self.client.post(f"/api/police/applications/{self.application_id}/verification", json=payload)
        self.assertEqual(response.status_code, 400)

    def test_not_clear_changes_application_to_rejected(self):
        self.login()
        response = self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload("NOT_CLEAR", "Applicant could not be found at the address."))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["data"]["verification_status"], "NOT_CLEAR")
        self.assertEqual(db.session.get(Application, self.application.id).status, "REJECTED")

    def test_finalized_verification_cannot_be_submitted_twice(self):
        self.login()
        self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload()).status_code, 201)
        db.session.get(Application, self.application.id).status = "POLICE_VERIFICATION"
        db.session.commit()
        response = self.client.put(f"/api/police/applications/{self.application_id}/verification", json=self.verification_payload("NOT_CLEAR", "A second result is not allowed."))
        self.assertEqual(response.status_code, 409)

    def test_police_cannot_set_future_passport_statuses(self):
        self.login()
        for result in ("PASSPORT_GENERATED", "PASSPORT_DISPATCHED"):
            payload = self.verification_payload()
            payload["verification_status"] = result
            self.assertEqual(self.client.post(f"/api/police/applications/{self.application_id}/verification", json=payload).status_code, 400)
        self.assertEqual(db.session.get(Application, self.application.id).status, "POLICE_VERIFICATION")


if __name__ == "__main__":
    unittest.main()
