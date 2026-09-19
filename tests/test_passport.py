import os
import unittest
from datetime import date, timedelta

from app import create_app
from backend.extensions import db
from backend.models import Application, PoliceVerification, User


class PassportGenerationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "PASSPORT_VALIDITY_YEARS": 10,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.applicant = self._user("Applicant", "applicant@example.com", "applicant")
        self.other_applicant = self._user("Other Applicant", "other@example.com", "applicant")
        self.officer = self._user("Officer", "officer@example.com", "officer")
        self.police = self._user("Police", "police@example.com", "police")
        self.admin = self._user("Admin", "admin@example.com", "admin")
        db.session.add_all([self.applicant, self.other_applicant, self.officer, self.police, self.admin])
        db.session.flush()
        self.approved = self._application("PSP202600000010", self.applicant.id, "APPROVED")
        self.pending = self._application("PSP202600000011", self.applicant.id, "POLICE_VERIFICATION")
        self.rejected = self._application("PSP202600000012", self.applicant.id, "REJECTED")
        self.other_approved = self._application("PSP202600000013", self.other_applicant.id, "APPROVED")
        db.session.add_all([self.approved, self.pending, self.rejected, self.other_approved])
        db.session.flush()
        db.session.add(PoliceVerification(application_id=self.approved.id, police_officer_id=self.police.id, verification_status="CLEAR", verification_date=date.today()))
        db.session.add(PoliceVerification(application_id=self.other_approved.id, police_officer_id=self.police.id, verification_status="CLEAR", verification_date=date.today()))
        db.session.commit()

    @staticmethod
    def _user(name, email, role):
        user = User(full_name=name, email=email, password_hash="", phone="+1 555 123 4567", address="Test address", role=role)
        user.set_password("Password@123")
        return user

    @staticmethod
    def _application(application_id, applicant_id, status):
        return Application(application_id=application_id, applicant_id=applicant_id, application_type="NEW", status=status, personal_details={}, address_details={}, family_details={}, passport_details={})

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def login(self, role):
        emails = {"applicant": "applicant@example.com", "officer": "officer@example.com", "police": "police@example.com", "admin": "admin@example.com"}
        return self.client.post("/api/auth/login", json={"email": emails[role], "password": "Password@123"})

    def test_unauthenticated_user_cannot_generate_or_retrieve(self):
        self.assertEqual(self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/api/passports/{self.approved.application_id}").status_code, 401)

    def test_applicant_police_and_officer_cannot_generate(self):
        for role in ("applicant", "police", "officer"):
            self.login(role)
            response = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
            self.assertEqual(response.status_code, 403)
            self.client.post("/api/auth/logout")

    def test_admin_can_list_eligible_applications(self):
        self.login("admin")
        response = self.client.get("/api/admin/passports/eligible")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["application_id"] for item in response.json["data"]}, {"PSP202600000010", "PSP202600000013"})

    def test_only_approved_applications_can_generate(self):
        self.login("admin")
        for application_id in (self.pending.application_id, self.rejected.application_id):
            response = self.client.post(f"/api/admin/passports/generate/{application_id}")
            self.assertEqual(response.status_code, 400)

    def test_approved_without_clear_verification_cannot_generate(self):
        self.login("admin")
        self.approved.police_verification.verification_status = "NOT_CLEAR"
        db.session.commit()
        response = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        self.assertEqual(response.status_code, 422)

    def test_missing_application_returns_404(self):
        self.login("admin")
        response = self.client.post("/api/admin/passports/generate/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_admin_generation_creates_server_controlled_passport(self):
        self.login("admin")
        requested_issue = (date.today() - timedelta(days=100)).isoformat()
        response = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}", json={"passport_number": "CLIENT-CONTROLLED", "issue_date": requested_issue, "expiry_date": requested_issue, "status": "PASSPORT_GENERATED"})
        self.assertEqual(response.status_code, 201)
        passport = response.json["data"]
        self.assertTrue(passport["passport_number"].startswith(f"PAS{date.today().year}"))
        self.assertNotEqual(passport["passport_number"], "CLIENT-CONTROLLED")
        self.assertEqual(passport["issue_date"], date.today().isoformat())
        self.assertEqual(passport["expiry_date"], date(date.today().year + 10, date.today().month, date.today().day).isoformat())
        self.assertEqual(db.session.get(Application, self.approved.id).status, "PASSPORT_GENERATED")
        self.assertIsNotNone(db.session.get(Application, self.approved.id).passport)

    def test_duplicate_generation_is_rejected(self):
        self.login("admin")
        first = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        second = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(len(self.approved.passport.application.passport.to_dict()), 6)

    def test_passport_number_and_application_are_unique(self):
        self.login("admin")
        first = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        second = self.client.post(f"/api/admin/passports/generate/{self.other_approved.application_id}")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.json["data"]["passport_number"], second.json["data"]["passport_number"])
        self.assertEqual(db.session.query(Application).filter(Application.status == "PASSPORT_GENERATED").count(), 2)

    def test_applicant_can_retrieve_own_passport_read_only(self):
        self.login("admin")
        self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        self.client.post("/api/auth/logout")
        self.login("applicant")
        response = self.client.get(f"/api/passports/{self.approved.application_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["passport_status"], "PASSPORT_GENERATED")

    def test_applicant_cannot_retrieve_another_applicants_passport(self):
        self.login("admin")
        self.client.post(f"/api/admin/passports/generate/{self.other_approved.application_id}")
        self.client.post("/api/auth/logout")
        self.login("applicant")
        response = self.client.get(f"/api/passports/{self.other_approved.application_id}")
        self.assertEqual(response.status_code, 404)

    def test_officer_and_police_cannot_retrieve_passport(self):
        self.login("admin")
        self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        for role in ("officer", "police"):
            self.client.post("/api/auth/logout")
            self.login(role)
            self.assertEqual(self.client.get(f"/api/passports/{self.approved.application_id}").status_code, 403)

    def test_admin_can_retrieve_passport(self):
        self.login("admin")
        self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}")
        response = self.client.get(f"/api/passports/{self.approved.application_id}")
        self.assertEqual(response.status_code, 200)

    def test_future_statuses_are_not_set_by_generation_request(self):
        self.login("admin")
        response = self.client.post(f"/api/admin/passports/generate/{self.approved.application_id}", json={"status": "PASSPORT_DISPATCHED"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["data"]["passport_status"], "PASSPORT_GENERATED")


if __name__ == "__main__":
    unittest.main()
