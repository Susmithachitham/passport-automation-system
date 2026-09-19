import unittest

from app import create_app
from backend.extensions import db


def registration_payload(email="person@example.com"):
    return {
        "full_name": "Test Person",
        "email": email,
        "password": "Password@123",
        "phone": "+1 555 123 4567",
        "address": "1 Test Street",
    }


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.drop_all()
        self.context.pop()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])


    def test_successful_registration(self):
        response = self.client.post("/api/auth/register", json=registration_payload())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["role"], "applicant")


    def test_duplicate_email(self):
        self.client.post("/api/auth/register", json=registration_payload())
        response = self.client.post("/api/auth/register", json=registration_payload())
        self.assertEqual(response.status_code, 409)


    def test_invalid_registration(self):
        response = self.client.post("/api/auth/register", json={"email": "bad"})
        self.assertEqual(response.status_code, 400)


    def test_successful_login(self):
        self.client.post("/api/auth/register", json=registration_payload())
        response = self.client.post("/api/auth/login", json={
            "email": "person@example.com",
            "password": "Password@123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["role"], "applicant")


    def test_invalid_login(self):
        self.client.post("/api/auth/register", json=registration_payload())
        response = self.client.post("/api/auth/login", json={
            "email": "person@example.com",
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 401)


    def test_current_user_endpoint(self):
        self.client.post("/api/auth/register", json=registration_payload())
        self.client.post("/api/auth/login", json={"email": "person@example.com", "password": "Password@123"})
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["email"], "person@example.com")


    def test_logout(self):
        self.client.post("/api/auth/register", json=registration_payload())
        self.client.post("/api/auth/login", json={"email": "person@example.com", "password": "Password@123"})
        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)


    def test_unauthorized_access(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)


    def test_role_information(self):
        self.client.post("/api/auth/register", json=registration_payload())
        response = self.client.post("/api/auth/login", json={"email": "person@example.com", "password": "Password@123"})
        self.assertEqual(response.json["user"]["role"], "applicant")


if __name__ == "__main__":
    unittest.main()
