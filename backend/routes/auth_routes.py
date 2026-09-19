import re

from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models.user import User
from backend.utils.auth import login_required


auth_bp = Blueprint("auth", __name__)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s().-]{6,18}[0-9]$")
ALLOWED_ROLES = {"applicant", "officer", "police", "admin"}


def _payload():
    return request.get_json(silent=True) or {}


def _validate_registration(data):
    required_fields = ("full_name", "email", "password", "phone", "address")
    missing = [field for field in required_fields if not str(data.get(field, "")).strip()]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    if not EMAIL_PATTERN.fullmatch(data["email"].strip()):
        return "Please provide a valid email address"
    if len(data["password"]) < 8:
        return "Password must be at least 8 characters long"
    if not PHONE_PATTERN.fullmatch(data["phone"].strip()):
        return "Please provide a valid phone number"
    return None


@auth_bp.post("/register")
def register():
    data = _payload()
    validation_error = _validate_registration(data)
    if validation_error:
        return jsonify(success=False, message=validation_error), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(success=False, message="An account with this email already exists"), 409

    user = User(
        full_name=data["full_name"].strip(),
        email=email,
        phone=data["phone"].strip(),
        address=data["address"].strip(),
        role="applicant",
    )
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, message="An account with this email already exists"), 409

    return jsonify(success=True, message="Registration successful", user=user.to_dict()), 201


@auth_bp.post("/login")
def login():
    data = _payload()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    user = User.query.filter_by(email=email).first()
    if not user or not isinstance(password, str) or not user.check_password(password):
        return jsonify(success=False, message="Invalid email or password"), 401
    if not user.is_active:
        return jsonify(success=False, message="This account is inactive"), 403

    session.clear()
    session["user_id"] = user.id
    session["user_role"] = user.role
    return jsonify(success=True, message="Login successful", user=user.to_dict())


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(success=True, message="Logout successful")


@auth_bp.get("/me")
@login_required
def current_user():
    return jsonify(success=True, user=request.current_user.to_dict())
