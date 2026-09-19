import io
import os
import unittest

from app import create_app
from backend.extensions import db
from backend.models.user import User


class ApplicantWorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "UPLOAD_FOLDER": os.path.join(os.getcwd(), "uploads", "documents", "test"),
            "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,
        })
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _register(self, email="applicant@example.com", password="Password@123"):
        return self.client.post(
            "/api/auth/register",
            json={
                "full_name": "Applicant User",
                "email": email,
                "password": password,
                "phone": "+1 555 123 4567",
                "address": "1 Demo Street",
            },
        )

    def _login(self, email="applicant@example.com", password="Password@123"):
        return self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )

    def test_create_application_and_get_own_applications(self):
        self._register()
        self._login()

        create_response = self.client.post("/api/applications", json={"application_type": "NEW"})
        self.assertEqual(create_response.status_code, 201)
        app_id = create_response.json["data"]["application_id"]

        list_response = self.client.get("/api/applications")
        self.assertEqual(list_response.status_code, 200)
        self.assertGreater(len(list_response.json["data"]), 0)

        detail_response = self.client.get(f"/api/applications/{app_id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json["data"]["application_type"], "NEW")

    def test_cannot_access_another_applicant_application(self):
        self._register("first@example.com")
        self._login("first@example.com")
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        self.client.post("/api/auth/logout")
        self._register("second@example.com")
        self._login("second@example.com")

        response = self.client.get(f"/api/applications/{app_id}")
        self.assertEqual(response.status_code, 403)

    def test_update_draft_application(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        update = self.client.put(
            f"/api/applications/{app_id}",
            json={
                "personal_details": {
                    "full_name": "Applicant User",
                    "date_of_birth": "2000-01-12",
                    "gender": "Male",
                    "place_of_birth": "Delhi",
                    "father_name": "Father User",
                    "mother_name": "Mother User",
                    "marital_status": "Single",
                    "nationality": "Indian",
                    "mobile_number": "+91 9876543210",
                    "email": "applicant@example.com",
                }
            },
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json["data"]["personal_details"]["gender"], "Male")

    def test_upload_valid_document_and_reject_invalid(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        pdf = (io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "identity_proof.pdf")
        upload = self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Identity Proof", "document": (pdf[0], pdf[1], "application/pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload.status_code, 201)

        invalid = self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Identity Proof", "document": (io.BytesIO(b"bad"), "bad.exe", "application/x-msdownload")},
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid.status_code, 400)

    def test_reject_oversized_file(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        large_data = b"a" * (6 * 1024 * 1024)
        response = self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Identity Proof", "document": (io.BytesIO(large_data), "large.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)

    def test_cannot_submit_incomplete_application(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        response = self.client.post(f"/api/applications/{app_id}/submit", json={"confirmation": True})
        self.assertEqual(response.status_code, 400)

    def test_cannot_submit_without_payment(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        self.client.put(
            f"/api/applications/{app_id}",
            json={
                "personal_details": {"full_name": "Applicant User", "date_of_birth": "2000-01-12", "gender": "Male", "place_of_birth": "Delhi", "father_name": "Father User", "mother_name": "Mother User", "marital_status": "Single", "nationality": "Indian", "mobile_number": "+91 9876543210", "email": "applicant@example.com"},
                "address_details": {"current_address": {"house_number": "A-1", "street": "Main Road", "area": "Dwarka", "city": "Delhi", "district": "New Delhi", "state": "Delhi", "pincode": "110078"}, "permanent_address": {"house_number": "A-1", "street": "Main Road", "area": "Dwarka", "city": "Delhi", "district": "New Delhi", "state": "Delhi", "pincode": "110078"}},
                "family_details": {"father_name": "Father User", "mother_name": "Mother User"},
                "passport_details": {"previous_passport_held": "No"},
            },
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Identity Proof", "document": (io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "identity.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )

        response = self.client.post(f"/api/applications/{app_id}/submit", json={"confirmation": True})
        self.assertEqual(response.status_code, 400)

    def test_successful_mock_payment_sets_application_to_submitted(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        self.client.put(
            f"/api/applications/{app_id}",
            json={
                "personal_details": {"full_name": "Applicant User", "date_of_birth": "2000-01-12", "gender": "Male", "place_of_birth": "Delhi", "father_name": "Father User", "mother_name": "Mother User", "marital_status": "Single", "nationality": "Indian", "mobile_number": "+91 9876543210", "email": "applicant@example.com"},
                "address_details": {"current_address": {"house_number": "A-1", "street": "Main Road", "area": "Dwarka", "city": "Delhi", "district": "New Delhi", "state": "Delhi", "pincode": "110078"}, "permanent_address": {"house_number": "A-1", "street": "Main Road", "area": "Dwarka", "city": "Delhi", "district": "New Delhi", "state": "Delhi", "pincode": "110078"}},
                "family_details": {"father_name": "Father User", "mother_name": "Mother User"},
                "passport_details": {"previous_passport_held": "No"},
            },
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Identity Proof", "document": (io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "identity.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Address Proof", "document": (io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "address.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Date of Birth Proof", "document": (io.BytesIO(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"), "dob.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Photograph", "document": (io.BytesIO(b"fakeimage"), "photo.jpg", "image/jpeg")},
            content_type="multipart/form-data",
        )
        self.client.post(
            f"/api/applications/{app_id}/documents",
            data={"document_type": "Signature", "document": (io.BytesIO(b"fakeimage"), "signature.jpg", "image/jpeg")},
            content_type="multipart/form-data",
        )

        payment = self.client.post(
            f"/api/applications/{app_id}/payment",
            json={"payment_method": "UPI"},
        )
        self.assertEqual(payment.status_code, 200)
        self.assertEqual(payment.json["data"]["payment_status"], "SUCCESS")

        status_response = self.client.get(f"/api/applications/{app_id}/status")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json["data"]["status"], "SUBMITTED")

    def test_cannot_arbitrarily_change_status(self):
        self._register()
        self._login()
        created = self.client.post("/api/applications", json={"application_type": "NEW"})
        app_id = created.json["data"]["application_id"]

        response = self.client.put(f"/api/applications/{app_id}", json={"status": "APPROVED"})
        self.assertEqual(response.status_code, 400)

    def test_profile_retrieval_update_and_change_password(self):
        self._register()
        self._login()

        profile = self.client.get("/api/profile")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["data"]["email"], "applicant@example.com")

        update = self.client.put("/api/profile", json={"phone": "+91 9988776655", "address": "Updated Address"})
        self.assertEqual(update.status_code, 200)

        password_change = self.client.post(
            "/api/profile/change-password",
            json={"current_password": "Password@123", "new_password": "NewPass@456", "confirm_password": "NewPass@456"},
        )
        self.assertEqual(password_change.status_code, 200)

        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)

        relogin = self.client.post("/api/auth/login", json={"email": "applicant@example.com", "password": "NewPass@456"})
        self.assertEqual(relogin.status_code, 200)


if __name__ == "__main__":
    unittest.main()
