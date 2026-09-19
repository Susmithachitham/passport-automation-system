import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app
from backend.extensions import db
from backend.models.user import User


DEMO_USERS = (
    ("Applicant", "applicant@example.com", "applicant", "DEMO_APPLICANT_PASSWORD"),
    ("Officer", "officer@example.com", "officer", "DEMO_OFFICER_PASSWORD"),
    ("Police", "police@example.com", "police", "DEMO_POLICE_PASSWORD"),
    ("Admin", "admin@example.com", "admin", "DEMO_ADMIN_PASSWORD"),
)


def seed_demo_users():
    load_dotenv()
    with app.app_context():
        for name, email, role, password_variable in DEMO_USERS:
            password = os.getenv(password_variable)
            if not password:
                raise RuntimeError(f"Set {password_variable} before running the seed script")
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User(
                    full_name=name,
                    email=email,
                    phone="+10000000000",
                    address="Demo account",
                    role=role,
                )
                user.set_password(password)
                db.session.add(user)
            else:
                user.full_name = name
                user.role = role
                user.is_active = True
                user.set_password(password)
        db.session.commit()
        print("Demo users seeded successfully.")


if __name__ == "__main__":
    seed_demo_users()
