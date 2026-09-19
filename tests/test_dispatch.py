import os
import unittest
from datetime import date

from app import create_app
from backend.extensions import db
from backend.models import Application, Dispatch, Passport, User


class DispatchWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SQLALCHEMY_TRACK_MODIFICATIONS": False, "PASSPORT_VALIDITY_YEARS": 10})
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
        self.generated = self._application("PSP202600000020", self.applicant.id, "PASSPORT_GENERATED")
        self.other_generated = self._application("PSP202600000021", self.other_applicant.id, "PASSPORT_GENERATED")
        self.generated.passport = Passport(passport_number="PAS2026DISPATCH01", issue_date=date.today(), expiry_date=date(date.today().year + 10, date.today().month, date.today().day))
        self.other_generated.passport = Passport(passport_number="PAS2026DISPATCH02", issue_date=date.today(), expiry_date=date(date.today().year + 10, date.today().month, date.today().day))
        self.pending_application = self._application("PSP202600000022", self.applicant.id, "APPROVED")
        db.session.add_all([self.generated, self.other_generated, self.pending_application])
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
        emails = {"applicant": "applicant@example.com", "other": "other@example.com", "officer": "officer@example.com", "police": "police@example.com", "admin": "admin@example.com"}
        return self.client.post("/api/auth/login", json={"email": emails[role], "password": "Password@123"})

    @staticmethod
    def payload():
        return {"courier_name": "Academic Courier", "tracking_number": "TRACK-2026-001", "delivery_method": "COURIER", "dispatch_remarks": "Manual academic dispatch record."}

    def test_unauthenticated_and_non_admin_cannot_dispatch(self):
        self.assertEqual(self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload()).status_code, 401)
        for role in ("applicant", "officer", "police"):
            self.login(role)
            self.assertEqual(self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload()).status_code, 403)
            self.client.post("/api/auth/logout")

    def test_admin_dashboard_and_queue_are_database_backed(self):
        self.login("admin")
        dashboard = self.client.get("/api/admin/dispatch/dashboard")
        queue = self.client.get("/api/admin/dispatch?search=PSP202600000020&status=PASSPORT_GENERATED&per_page=1")
        eligible = self.client.get("/api/admin/dispatch/eligible")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json["data"]["ready_for_dispatch"], 2)
        self.assertEqual(queue.status_code, 200)
        self.assertEqual({item["passport_number"] for item in queue.json["data"]["items"]}, {"PAS2026DISPATCH01"})
        self.assertEqual(queue.json["data"]["per_page"], 1)
        self.assertEqual(len(eligible.json["data"]), 2)

    def test_non_generated_states_are_not_dispatchable(self):
        self.login("admin")
        for status in ("DRAFT", "SUBMITTED", "DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED", "POLICE_VERIFICATION", "APPROVED", "REJECTED"):
            application = self._application(f"PSP2026{status[:4]}", self.applicant.id, status)
            db.session.add(application)
        db.session.commit()
        for application in Application.query.filter(Application.application_id.like("PSP2026%"), Application.status != "PASSPORT_GENERATED").all():
            response = self.client.post(f"/api/admin/dispatch/{application.application_id}", json=self.payload())
            self.assertIn(response.status_code, {400, 409})

    def test_admin_can_view_dispatch_details(self):
        self.login("admin")
        response = self.client.get(f"/api/admin/dispatch/{self.generated.application_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["data"]["passport"]["passport_number"], "PAS2026DISPATCH01")
        self.assertIsNone(response.json["data"]["dispatch"])

    def test_dispatch_validation_rejects_missing_invalid_and_oversized_values(self):
        self.login("admin")
        missing = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json={})
        invalid = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json={**self.payload(), "delivery_method": "TELEPORT"})
        oversized = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json={**self.payload(), "courier_name": "x" * 121})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(oversized.status_code, 400)

    def test_dispatch_is_server_controlled_and_atomic(self):
        self.login("admin")
        response = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json={**self.payload(), "dispatch_date": "2000-01-01", "status": "PASSPORT_GENERATED"})
        self.assertEqual(response.status_code, 201)
        data = response.json["data"]
        self.assertEqual(data["dispatched_by_id"], self.admin.id)
        self.assertNotEqual(data["dispatch_date"][:10], "2000-01-01")
        self.assertEqual(db.session.get(Application, self.generated.id).status, "PASSPORT_DISPATCHED")
        self.assertEqual(db.session.query(Dispatch).count(), 1)

    def test_duplicate_dispatch_returns_conflict_and_preserves_original(self):
        self.login("admin")
        first = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload())
        second = self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json={**self.payload(), "tracking_number": "SECOND"})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(db.session.query(Dispatch).count(), 1)
        self.assertEqual(db.session.query(Dispatch).first().tracking_number, "TRACK-2026-001")

    def test_applicant_can_view_only_own_dispatch(self):
        self.login("admin")
        self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload())
        self.client.post("/api/auth/logout")
        self.login("applicant")
        own = self.client.get(f"/api/dispatch/{self.generated.application_id}")
        other = self.client.get(f"/api/dispatch/{self.other_generated.application_id}")
        self.assertEqual(own.status_code, 200)
        self.assertEqual(own.json["data"]["tracking_number"], "TRACK-2026-001")
        self.assertEqual(other.status_code, 403)

    def test_applicant_sees_generated_awaiting_dispatch_and_cannot_modify(self):
        self.login("applicant")
        self.assertEqual(self.client.get(f"/api/dispatch/{self.generated.application_id}").status_code, 404)
        self.assertEqual(self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload()).status_code, 403)

    def test_officer_and_police_cannot_view_or_dispatch_admin_routes(self):
        for role in ("officer", "police"):
            self.login(role)
            self.assertEqual(self.client.get("/api/admin/dispatch").status_code, 403)
            self.assertEqual(self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload()).status_code, 403)
            self.client.post("/api/auth/logout")

    def test_admin_without_generated_passport_is_rejected(self):
        self.login("admin")
        response = self.client.post(f"/api/admin/dispatch/{self.pending_application.application_id}", json=self.payload())
        self.assertEqual(response.status_code, 409)

    def test_dispatch_detail_and_history_after_dispatch(self):
        self.login("admin")
        self.client.post(f"/api/admin/dispatch/{self.generated.application_id}", json=self.payload())
        detail = self.client.get(f"/api/admin/dispatch/{self.generated.application_id}")
        history = self.client.get("/api/admin/dispatch?status=PASSPORT_DISPATCHED")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["data"]["status"], "PASSPORT_DISPATCHED")
        self.assertEqual(detail.json["data"]["dispatch"]["dispatched_by_name"], "Admin")
        self.assertEqual(history.json["data"]["items"][0]["status"], "PASSPORT_DISPATCHED")


if __name__ == "__main__":
    unittest.main()
