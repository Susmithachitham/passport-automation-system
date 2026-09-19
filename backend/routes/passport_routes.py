import secrets
import string
from calendar import monthrange
from datetime import date

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models.application import Application
from backend.models.passport import Passport
from backend.utils.auth import login_required, role_required

passport_bp = Blueprint("passport", __name__)
APPROVED_STATUS = "APPROVED"


def json_response(success, message, data=None, status=200):
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _add_years(value, years):
    target_year = value.year + years
    return value.replace(year=target_year, day=min(value.day, monthrange(target_year, value.month)[1]))


def _generate_passport_number():
    year = date.today().year
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    return f"PAS{year}{suffix}"


def _get_application(application_id):
    application = Application.query.filter_by(application_id=application_id).first()
    if not application:
        return None, json_response(False, "Application not found", status=404)
    return application, None


def _get_passport(application_id):
    application, error_response = _get_application(application_id)
    if error_response:
        return None, error_response
    if not application.passport:
        return None, json_response(False, "Passport has not been generated for this application", status=404)
    return application.passport, None


@passport_bp.get("/admin/passports/eligible")
@login_required
@role_required("admin")
def eligible_applications():
    applications = Application.query.filter_by(status=APPROVED_STATUS).order_by(Application.updated_at.desc()).all()
    return json_response(True, "Eligible applications retrieved successfully", [
        {
            "application_id": application.application_id,
            "applicant_name": (application.applicant.full_name if application.applicant else "Unknown"),
            "status": application.status,
            "police_verification": application.police_verification.to_dict() if application.police_verification else None,
            "passport": application.passport.to_dict() if application.passport else None,
        }
        for application in applications
    ])


@passport_bp.post("/admin/passports/generate/<application_id>")
@login_required
@role_required("admin")
def generate_passport(application_id):
    application, error_response = _get_application(application_id)
    if error_response:
        return error_response
    if application.passport:
        return json_response(False, "Passport has already been generated for this application", status=409)
    if application.status != APPROVED_STATUS:
        return json_response(False, "Only approved applications can generate a passport", status=400)
    verification = application.police_verification
    if not verification or verification.verification_status != "CLEAR":
        return json_response(False, "A CLEAR police verification is required before passport generation", status=422)

    issue_date = date.today()
    expiry_date = _add_years(issue_date, current_app.config.get("PASSPORT_VALIDITY_YEARS", 10))
    for _ in range(5):
        passport = Passport(
            application_id=application.id,
            passport_number=_generate_passport_number(),
            issue_date=issue_date,
            expiry_date=expiry_date,
        )
        db.session.add(passport)
        application.status = "PASSPORT_GENERATED"
        try:
            db.session.commit()
            return json_response(True, "Passport generated successfully", passport.to_dict(), status=201)
        except IntegrityError:
            db.session.rollback()
            if Passport.query.filter_by(application_id=application.id).first():
                return json_response(False, "Passport has already been generated for this application", status=409)
    return json_response(False, "Unable to generate a unique passport number", status=500)


@passport_bp.get("/passports/<application_id>")
@login_required
def get_passport(application_id):
    if request.current_user.role not in {"admin", "applicant"}:
        return json_response(False, "Insufficient permissions", status=403)
    passport, error_response = _get_passport(application_id)
    if error_response:
        if request.current_user.role != "admin":
            application, _ = _get_application(application_id)
            if not application or application.applicant_id != request.current_user.id:
                return json_response(False, "Passport not found", status=404)
        else:
            return error_response
    if passport is None:
        return json_response(False, "Passport not found", status=404)
    if request.current_user.role != "admin" and passport.application.applicant_id != request.current_user.id:
        return json_response(False, "Passport not found", status=404)
    return json_response(True, "Passport retrieved successfully", passport.to_dict())