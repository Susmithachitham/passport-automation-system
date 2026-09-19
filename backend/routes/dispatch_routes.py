from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models.application import Application
from backend.models.dispatch import Dispatch
from backend.models.user import User
from backend.utils.auth import login_required, role_required

dispatch_bp = Blueprint("dispatch", __name__)
GENERATED_STATUS = "PASSPORT_GENERATED"
DISPATCHED_STATUS = "PASSPORT_DISPATCHED"
DELIVERY_METHODS = {"COURIER", "REGISTERED_MAIL", "POSTAL"}


def json_response(success, message, data=None, status=200):
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _application(application_id):
    application = Application.query.filter_by(application_id=application_id).first()
    if not application:
        return None, json_response(False, "Application not found", status=404)
    return application, None


def _dispatch_data(application):
    data = {
        "application_id": application.application_id,
        "applicant": application.applicant.to_dict() if application.applicant else None,
        "application_type": application.application_type,
        "status": application.status,
        "passport": application.passport.to_dict() if application.passport else None,
        "police_verification": application.police_verification.to_dict() if application.police_verification else None,
        "dispatch": application.dispatch.to_dict() if application.dispatch else None,
    }
    return data


def _validate_dispatch_payload(data):
    courier_name = str(data.get("courier_name", "")).strip()
    tracking_number = str(data.get("tracking_number", "")).strip()
    delivery_method = str(data.get("delivery_method", "")).strip().upper()
    remarks = str(data.get("dispatch_remarks", "")).strip()
    if not courier_name or len(courier_name) > 120:
        return None, "Courier name is required and must be 120 characters or fewer"
    if not tracking_number or len(tracking_number) > 120:
        return None, "Tracking number is required and must be 120 characters or fewer"
    if delivery_method not in DELIVERY_METHODS:
        return None, "Please select a valid delivery method"
    if len(remarks) > 2000:
        return None, "Dispatch remarks must be 2000 characters or fewer"
    return {"courier_name": courier_name, "tracking_number": tracking_number, "delivery_method": delivery_method, "dispatch_remarks": remarks or None}, None


def _applicant_can_view(application):
    return request.current_user.role == "admin" or (
        request.current_user.role == "applicant" and application.applicant_id == request.current_user.id
    )


@dispatch_bp.get("/admin/dispatch/dashboard")
@login_required
@role_required("admin")
def dashboard():
    generated = Application.query.filter_by(status=GENERATED_STATUS).count()
    dispatched = Application.query.filter_by(status=DISPATCHED_STATUS).count()
    recent = Dispatch.query.order_by(Dispatch.dispatch_date.desc()).limit(5).all()
    return json_response(True, "Dispatch dashboard retrieved successfully", {
        "total_generated_passports": generated + dispatched,
        "ready_for_dispatch": generated,
        "dispatched": dispatched,
        "recent_dispatches": [item.to_dict() for item in recent],
    })


@dispatch_bp.get("/admin/dispatch")
@login_required
@role_required("admin")
def list_dispatch_queue():
    query = Application.query.join(Application.applicant).filter(Application.status.in_([GENERATED_STATUS, DISPATCHED_STATUS]))
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip().upper()
    sort = request.args.get("sort", "newest").strip().lower()
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Application.application_id.ilike(term), User.full_name.ilike(term)))
    if status in {GENERATED_STATUS, DISPATCHED_STATUS}:
        query = query.filter(Application.status == status)
    query = query.order_by(Application.updated_at.asc() if sort == "oldest" else Application.updated_at.desc())
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for application in pagination.items:
        items.append({
            "application_id": application.application_id,
            "applicant_name": application.applicant.full_name if application.applicant else "Unknown",
            "passport_number": application.passport.passport_number if application.passport else None,
            "issue_date": application.passport.issue_date.isoformat() if application.passport else None,
            "expiry_date": application.passport.expiry_date.isoformat() if application.passport else None,
            "status": application.status,
            "dispatch": application.dispatch.to_dict() if application.dispatch else None,
        })
    return json_response(True, "Dispatch queue retrieved successfully", {"items": items, "page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages})


@dispatch_bp.get("/admin/dispatch/eligible")
@login_required
@role_required("admin")
def eligible_dispatches():
    applications = Application.query.filter_by(status=GENERATED_STATUS).filter(Application.passport.has()).order_by(Application.updated_at.desc()).all()
    return json_response(True, "Eligible dispatches retrieved successfully", [_dispatch_data(application) for application in applications if not application.dispatch])


@dispatch_bp.get("/admin/dispatch/<application_id>")
@login_required
@role_required("admin")
def get_admin_dispatch(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    return json_response(True, "Dispatch details retrieved successfully", _dispatch_data(application))


@dispatch_bp.post("/admin/dispatch/<application_id>")
@login_required
@role_required("admin")
def create_dispatch(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.dispatch or application.status == DISPATCHED_STATUS:
        return json_response(False, "Passport has already been dispatched for this application", status=409)
    if application.status != GENERATED_STATUS:
        return json_response(False, "Only generated passports can be dispatched", status=409)
    if not application.passport:
        return json_response(False, "A generated passport is required before dispatch", status=409)
    payload, validation_error = _validate_dispatch_payload(request.get_json(silent=True) or {})
    if validation_error:
        return json_response(False, validation_error, status=400)
    dispatch = Dispatch(
        application_id=application.id,
        passport_id=application.passport.id,
        dispatched_by_id=request.current_user.id,
        dispatch_date=datetime.now(timezone.utc),
        **payload,
    )
    db.session.add(dispatch)
    application.status = DISPATCHED_STATUS
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return json_response(False, "Passport has already been dispatched for this application", status=409)
    return json_response(True, "Passport dispatched successfully", dispatch.to_dict(), status=201)


@dispatch_bp.get("/dispatch/<application_id>")
@login_required
def get_applicant_dispatch(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if not _applicant_can_view(application):
        return json_response(False, "You cannot access another applicant's dispatch information", status=403 if request.current_user.role == "applicant" else 403)
    if not application.dispatch:
        return json_response(False, "Dispatch has not been recorded for this application", status=404)
    return json_response(True, "Dispatch details retrieved successfully", application.dispatch.to_dict())