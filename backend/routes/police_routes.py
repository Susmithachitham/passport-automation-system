from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from backend.extensions import db
from backend.models.application import Application
from backend.models.police_verification import PoliceVerification
from backend.models.user import User
from backend.utils.auth import login_required, role_required

police_bp = Blueprint("police", __name__)
POLICE_STATUS = "POLICE_VERIFICATION"
VALID_RESULTS = {"CLEAR", "NOT_CLEAR"}


def json_response(success, message, data=None, status=200):
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _get_eligible_application(application_id):
    application = Application.query.filter_by(application_id=application_id).first()
    if not application:
        return None, json_response(False, "Application not found", status=404)
    if application.status != POLICE_STATUS:
        return None, json_response(False, "Application is not eligible for Police verification", status=409)
    return application, None


def _verification(application):
    record = application.police_verification
    if record is None:
        record = PoliceVerification(application_id=application.id, police_officer_id=request.current_user.id)
        db.session.add(record)
        db.session.flush()
    return record


def _application_data(application):
    data = application.to_dict()
    data["applicant"] = application.applicant.to_dict() if application.applicant else None
    data["police_verification"] = application.police_verification.to_dict() if application.police_verification else None
    data["interview"] = application.interviews[-1].to_dict() if application.interviews else None
    return data


def _parse_bool(data, field):
    value = data.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be true or false")
    return value


def _validate_payload(data):
    result = str(data.get("verification_status", "")).strip().upper()
    if result not in VALID_RESULTS:
        return None, "verification_status must be CLEAR or NOT_CLEAR"
    try:
        fields = {
            "address_verified": _parse_bool(data, "address_verified"),
            "identity_verified": _parse_bool(data, "identity_verified"),
            "applicant_found": _parse_bool(data, "applicant_found"),
            "criminal_record_found": _parse_bool(data, "criminal_record_found"),
        }
    except ValueError as error:
        return None, str(error)
    remarks = str(data.get("remarks", "")).strip()
    if result == "CLEAR":
        if not fields["address_verified"] or not fields["identity_verified"] or not fields["applicant_found"]:
            return None, "Address, identity, and applicant verification must be complete before clearing"
        if fields["criminal_record_found"]:
            return None, "A case with a criminal record cannot be marked CLEAR"
    elif len(remarks) < 5:
        return None, "Meaningful remarks are required when verification is NOT_CLEAR"
    return {**fields, "verification_status": result, "remarks": remarks or None}, None


def _save_verification(application, data):
    payload, error = _validate_payload(data)
    if error:
        return None, json_response(False, error, status=400)
    record = application.police_verification
    if record and record.verification_status in {"CLEAR", "NOT_CLEAR"}:
        return None, json_response(False, "Police verification has already been finalized", status=409)
    record = _verification(application)
    for field in ("address_verified", "identity_verified", "applicant_found", "criminal_record_found", "verification_status", "remarks"):
        setattr(record, field, payload[field])
    record.police_officer_id = request.current_user.id
    record.verification_date = datetime.now(timezone.utc)
    application.status = "APPROVED" if payload["verification_status"] == "CLEAR" else "REJECTED"
    db.session.commit()
    return record, None


@police_bp.get("/dashboard")
@login_required
@role_required("police")
def dashboard():
    records = PoliceVerification.query
    total = records.count()
    clear = records.filter_by(verification_status="CLEAR").count()
    not_clear = records.filter_by(verification_status="NOT_CLEAR").count()
    pending = Application.query.filter_by(status=POLICE_STATUS).count()
    recent = Application.query.filter_by(status=POLICE_STATUS).order_by(Application.forwarded_at.desc()).limit(5).all()
    return json_response(True, "Police dashboard retrieved successfully", {
        "total_cases": total + pending,
        "pending_verification": pending,
        "clear_cases": clear,
        "not_clear_cases": not_clear,
        "recently_assigned_cases": [application.application_id for application in recent],
    })


@police_bp.get("/applications")
@login_required
@role_required("police")
def list_applications():
    query = Application.query.join(Application.applicant).filter(Application.status == POLICE_STATUS)
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "newest").strip().lower()
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Application.application_id.ilike(term), Application.application_type.ilike(term), User.full_name.ilike(term)))
    if sort == "oldest":
        query = query.order_by(Application.forwarded_at.asc(), Application.created_at.asc())
    else:
        query = query.order_by(Application.forwarded_at.desc(), Application.created_at.desc())
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for application in pagination.items:
        record = application.police_verification
        items.append({
            "application_id": application.application_id,
            "applicant_name": application.applicant.full_name if application.applicant else "Unknown",
            "application_type": application.application_type,
            "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
            "forwarded_at": application.forwarded_at.isoformat() if application.forwarded_at else None,
            "status": application.status,
            "verification_status": record.verification_status if record else "PENDING",
            "interview": application.interviews[-1].to_dict() if application.interviews else None,
        })
    return json_response(True, "Police applications retrieved successfully", {"items": items, "page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages})


@police_bp.get("/applications/<application_id>")
@login_required
@role_required("police")
def get_application(application_id):
    application, error_response = _get_eligible_application(application_id)
    if error_response:
        return error_response
    return json_response(True, "Police application retrieved successfully", _application_data(application))


@police_bp.get("/applications/<application_id>/verification")
@login_required
@role_required("police")
def get_verification(application_id):
    application, error_response = _get_eligible_application(application_id)
    if error_response:
        return error_response
    record = application.police_verification
    return json_response(True, "Police verification retrieved successfully", record.to_dict() if record else {"verification_status": "PENDING"})


@police_bp.post("/applications/<application_id>/verification")
@police_bp.put("/applications/<application_id>/verification")
@login_required
@role_required("police")
def save_verification(application_id):
    application, error_response = _get_eligible_application(application_id)
    if error_response:
        return error_response
    record, error_response = _save_verification(application, request.get_json(silent=True) or {})
    if error_response:
        return error_response
    return json_response(True, "Police verification recorded successfully", record.to_dict(), status=201 if request.method == "POST" else 200)