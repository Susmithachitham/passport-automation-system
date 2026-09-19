import os
import unittest
from datetime import date, timedelta

from app import create_app
from backend.extensions import db
from backend.models import Application, Document, Interview, Payment, User


class OfficerWorkflowTestCase(unittest.TestCase):
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
        self.applicant = User(full_name="Applicant User", email="applicant@example.com", password_hash="", phone="+1 555 123 4567", address="Applicant address", role="applicant")
        self.applicant.set_password("Password@123")
        self.officer = User(full_name="Officer User", email="officer@example.com", password_hash="", phone="+1 555 222 4567", address="Officer address", role="officer")
        self.officer.set_password("Password@123")
        db.session.add_all([self.applicant, self.officer])
        db.session.flush()
        self.application = Application(
            application_id="PSP202600000001", applicant_id=self.applicant.id, application_type="NEW", status="SUBMITTED",
            personal_details={"full_name": "Applicant User", "date_of_birth": "2000-01-12", "gender": "Male", "place_of_birth": "Delhi", "nationality": "Indian", "mobile_number": "+91 9876543210", "email": "applicant@example.com", "father_name": "Father", "mother_name": "Mother"},
            address_details={"current_address": {"city": "Delhi"}, "permanent_address": {"city": "Delhi"}},
            family_details={"father_name": "Father", "mother_name": "Mother"}, passport_details={"previous_passport_held": "No"},
        )
        db.session.add(self.application)
        db.session.flush()
        self.documents = []
        for document_type in ("Identity Proof", "Address Proof", "Date of Birth Proof", "Photograph", "Signature"):
            document = Document(application_id=self.application.id, document_type=document_type, original_filename=f"{document_type}.pdf", stored_filename=f"{document_type}.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf", file_size=100)
            self.documents.append(document)
            db.session.add(document)
        db.session.add(Payment(application_id=self.application.id, transaction_id="TXN-2026-TEST001", amount=1500, payment_method="UPI", payment_status="SUCCESS"))
        db.session.commit()
        self.application_id = self.application.application_id

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, user_type="officer"):
        email = "officer@example.com" if user_type == "officer" else "applicant@example.com"
        return self.client.post("/api/auth/login", json={"email": email, "password": "Password@123"})

    def verify_all_documents(self):
        for document in self.documents:
            response = self.client.post(f"/api/officer/applications/{self.application_id}/documents/{document.id}/verify")
            self.assertEqual(response.status_code, 200)

    def schedule_interview(self):
        tomorrow = date.today() + timedelta(days=1)
        return self.client.post(f"/api/officer/applications/{self.application_id}/interview", json={"scheduled_date": tomorrow.isoformat(), "scheduled_time": "10:30", "location": "Passport Office"})

    def test_applicant_cannot_access_officer_dashboard(self):
        self.login("applicant")
        self.assertEqual(self.client.get("/api/officer/dashboard").status_code, 403)

    def test_applicant_cannot_access_officer_application(self):
        self.login("applicant")
        self.assertEqual(self.client.get(f"/api/officer/applications/{self.application_id}").status_code, 403)

    def test_unauthenticated_officer_api_is_denied(self):
        self.assertEqual(self.client.get("/api/officer/applications").status_code, 401)

    def test_officer_can_access_dashboard(self):
        self.login()
        response = self.client.get("/api/officer/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["new_applications"], 1)

    def test_officer_can_list_and_search_applications(self):
        self.login()
        response = self.client.get("/api/officer/applications?search=Applicant%20User&application_type=NEW&sort=oldest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["items"][0]["application_id"], self.application_id)

    def test_officer_can_view_application_and_documents(self):
        self.login()
        detail = self.client.get(f"/api/officer/applications/{self.application_id}")
        documents = self.client.get(f"/api/officer/applications/{self.application_id}/documents")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["data"]["applicant"]["email"], "applicant@example.com")
        self.assertEqual(len(documents.json["data"]), 5)

    def test_missing_application_and_unrelated_document_are_denied(self):
        self.login()
        self.assertEqual(self.client.get("/api/officer/applications/does-not-exist").status_code, 404)
        self.assertEqual(self.client.post(f"/api/officer/applications/{self.application_id}/documents/99999/verify").status_code, 404)

    def test_verifying_all_documents_moves_application_to_document_verification(self):
        self.login()
        self.verify_all_documents()
        self.assertEqual(self.client.get(f"/api/officer/applications/{self.application_id}").json["data"]["status"], "DOCUMENT_VERIFICATION")

    def test_officer_can_reject_document_with_reason(self):
        self.login()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/documents/{self.documents[0].id}/reject", json={"reason": "Image is unclear; upload a clearer copy."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["verification_status"], "REJECTED")
        self.assertIn("unclear", response.json["data"]["rejection_reason"])

    def test_document_rejection_requires_meaningful_reason(self):
        self.login()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/documents/{self.documents[0].id}/reject", json={"reason": "no"})
        self.assertEqual(response.status_code, 400)

    def test_applicant_can_see_document_rejection(self):
        self.login()
        self.client.post(f"/api/officer/applications/{self.application_id}/documents/{self.documents[0].id}/reject", json={"reason": "Identity proof is unreadable."})
        self.client.post("/api/auth/logout")
        self.login("applicant")
        response = self.client.get(f"/api/applications/{self.application_id}/documents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"][0]["verification_status"], "REJECTED")

    def test_cannot_schedule_before_documents_are_verified(self):
        self.login()
        response = self.schedule_interview()
        self.assertEqual(response.status_code, 409)

    def test_cannot_schedule_interview_in_past(self):
        self.login()
        self.verify_all_documents()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/interview", json={"scheduled_date": (date.today() - timedelta(days=1)).isoformat(), "scheduled_time": "10:30", "location": "Passport Office"})
        self.assertEqual(response.status_code, 400)

    def test_officer_can_schedule_valid_interview(self):
        self.login()
        self.verify_all_documents()
        response = self.schedule_interview()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["data"]["status"], "SCHEDULED")
        self.assertEqual(self.client.get(f"/api/officer/applications/{self.application_id}").json["data"]["status"], "INTERVIEW_SCHEDULED")

    def test_duplicate_active_interview_is_rejected(self):
        self.login()
        self.verify_all_documents()
        self.assertEqual(self.schedule_interview().status_code, 201)
        self.assertEqual(self.schedule_interview().status_code, 409)

    def test_officer_can_complete_or_mark_interview_missed(self):
        self.login()
        self.verify_all_documents()
        self.schedule_interview()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/interview/complete", json={"status": "COMPLETED", "officer_remarks": "Interview completed."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["status"], "COMPLETED")

    def test_forward_requires_completed_interview(self):
        self.login()
        self.verify_all_documents()
        self.schedule_interview()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/forward-to-police")
        self.assertEqual(response.status_code, 409)

    def test_officer_can_forward_eligible_application_to_police(self):
        self.login()
        self.verify_all_documents()
        self.schedule_interview()
        self.client.post(f"/api/officer/applications/{self.application_id}/interview/complete", json={"status": "COMPLETED"})
        response = self.client.post(f"/api/officer/applications/{self.application_id}/forward-to-police")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["status"], "POLICE_VERIFICATION")
        self.assertIsNotNone(response.json["data"]["forwarded_at"])

    def test_officer_can_reject_application_with_reason(self):
        self.login()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/reject", json={"reason": "Application requires correction."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["status"], "REJECTED")
        self.assertEqual(response.json["data"]["rejection_reason"], "Application requires correction.")

    def test_application_rejection_requires_reason(self):
        self.login()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/reject", json={"reason": ""})
        self.assertEqual(response.status_code, 400)

    def test_officer_cannot_reject_police_verification_or_set_future_status(self):
        self.login()
        self.application.status = "POLICE_VERIFICATION"
        db.session.commit()
        response = self.client.post(f"/api/officer/applications/{self.application_id}/reject", json={"reason": "Not allowed now."})
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("status", response.json.get("data", {}))


if __name__ == "__main__":
    unittest.main()
