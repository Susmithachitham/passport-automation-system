from datetime import date, datetime, time, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from backend.config import DOCUMENT_REQUIREMENTS
from backend.extensions import db
from backend.models.application import Application
from backend.models.document import Document
from backend.models.interview import Interview
from backend.models.payment import Payment
from backend.models.user import User
from backend.utils.auth import login_required, role_required

officer_bp = Blueprint("officer", __name__)
OFFICER_QUEUE_STATUSES = {"SUBMITTED", "DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED", "POLICE_VERIFICATION", "APPROVED", "REJECTED"}
ACTIVE_INTERVIEW_STATUSES = {"SCHEDULED"}
INTERVIEW_OUTCOMES = {"COMPLETED", "MISSED", "CANCELLED"}


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


def _required_documents_verified(application):
    documents = {document.document_type: document for document in application.documents}
    required = DOCUMENT_REQUIREMENTS.get(application.application_type, [])
    missing = [name for name in required if name not in documents]
    unverified = [name for name in required if name in documents and documents[name].verification_status != "VERIFIED"]
    return not missing and not unverified, missing, unverified


def _document_status(application):
    complete, missing, unverified = _required_documents_verified(application)
    if missing:
        return "MISSING"
    if complete:
        return "VERIFIED"
    if any(document.verification_status == "REJECTED" for document in application.documents):
        return "REJECTED"
    return "PENDING"


def _interview(application):
    return Interview.query.filter_by(application_id=application.id).order_by(Interview.created_at.desc()).first()


def _application_data(application):
    data = application.to_dict()
    data["applicant"] = application.applicant.to_dict() if application.applicant else None
    data["document_status"] = _document_status(application)
    interview = _interview(application)
    data["interview"] = interview.to_dict() if interview else None
    return data


def _parse_schedule(data):
    try:
        scheduled_date = date.fromisoformat(str(data.get("scheduled_date", "")))
        scheduled_time = time.fromisoformat(str(data.get("scheduled_time", "")))
    except ValueError:
        return None, None, "Please provide a valid interview date and time"
    if scheduled_date < date.today() or (scheduled_date == date.today() and scheduled_time <= datetime.now().time()):
        return None, None, "Interview cannot be scheduled in the past"
    location = str(data.get("location", "")).strip()
    if not location:
        return None, None, "Interview location is required"
    mode = str(data.get("interview_mode", "IN_PERSON")).strip().upper()
    if mode != "IN_PERSON":
        return None, None, "Only in-person interviews are supported"
    return (scheduled_date, scheduled_time, location, mode), None, None


@officer_bp.get("/dashboard")
@login_required
@role_required("officer")
def dashboard():
    counts = {
        "new_applications": Application.query.filter_by(status="SUBMITTED").count(),
        "pending_document_verification": Application.query.filter_by(status="DOCUMENT_VERIFICATION").count(),
        "interviews_scheduled": Interview.query.filter_by(status="SCHEDULED").count(),
        "pending_police_verification": Application.query.filter_by(status="POLICE_VERIFICATION").count(),
        "approved_applications": Application.query.filter_by(status="APPROVED").count(),
        "rejected_applications": Application.query.filter_by(status="REJECTED").count(),
    }
    return json_response(True, "Officer dashboard retrieved successfully", counts)


@officer_bp.get("/applications")
@login_required
@role_required("officer")
def list_applications():
    query = Application.query.join(Application.applicant).filter(Application.status.in_(OFFICER_QUEUE_STATUSES))
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip().upper()
    application_type = request.args.get("application_type", "").strip().upper()
    sort = request.args.get("sort", "newest").strip().lower()
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Application.application_id.ilike(term), Application.application_type.ilike(term), User.full_name.ilike(term)))
    if status in OFFICER_QUEUE_STATUSES:
        query = query.filter(Application.status == status)
    if application_type in {"NEW", "RENEWAL", "REISSUE"}:
        query = query.filter(Application.application_type == application_type)
    if sort == "oldest":
        query = query.order_by(Application.created_at.asc())
    elif sort == "status":
        query = query.order_by(Application.status.asc(), Application.created_at.desc())
    else:
        query = query.order_by(Application.created_at.desc())
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    data = []
    for application in pagination.items:
        item = _application_data(application)
        item["applicant_name"] = application.applicant.full_name if application.applicant else "Unknown"
        data.append(item)
    return json_response(True, "Officer applications retrieved successfully", {"items": data, "page": page, "per_page": per_page, "total": pagination.total, "pages": pagination.pages})


@officer_bp.get("/applications/<application_id>")
@login_required
@role_required("officer")
def get_application(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status == "DRAFT":
        return json_response(False, "Application is not available for officer review", status=404)
    return json_response(True, "Application retrieved successfully", _application_data(application))


@officer_bp.get("/applications/<application_id>/documents")
@login_required
@role_required("officer")
def list_documents(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    return json_response(True, "Application documents retrieved successfully", [document.to_dict() for document in application.documents])


def _get_document(application, document_id):
    document = Document.query.filter_by(id=document_id, application_id=application.id).first()
    if not document:
        return None, json_response(False, "Document not found for this application", status=404)
    return document, None


@officer_bp.post("/applications/<application_id>/documents/<int:document_id>/verify")
@login_required
@role_required("officer")
def verify_document(application_id, document_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status in {"POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED", "REJECTED"}:
        return json_response(False, "Documents cannot be changed after the officer workflow has advanced", status=409)
    document, error_response = _get_document(application, document_id)
    if error_response:
        return error_response
    document.verification_status = "VERIFIED"
    document.rejection_reason = None
    document.verification_remarks = str((request.get_json(silent=True) or {}).get("remarks", "")).strip() or None
    document.verified_by_id = request.current_user.id
    document.verified_at = datetime.now(timezone.utc)
    complete, _, _ = _required_documents_verified(application)
    if complete and application.status == "SUBMITTED":
        application.status = "DOCUMENT_VERIFICATION"
    db.session.commit()
    return json_response(True, "Document verified successfully", document.to_dict())


@officer_bp.post("/applications/<application_id>/documents/<int:document_id>/reject")
@login_required
@role_required("officer")
def reject_document(application_id, document_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status in {"POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED", "REJECTED"}:
        return json_response(False, "Documents cannot be changed after the officer workflow has advanced", status=409)
    document, error_response = _get_document(application, document_id)
    if error_response:
        return error_response
    data = request.get_json(silent=True) or {}
    reason = str(data.get("reason", "")).strip()
    if len(reason) < 5:
        return json_response(False, "A meaningful rejection reason is required", status=400)
    document.verification_status = "REJECTED"
    document.rejection_reason = reason
    document.verification_remarks = reason
    document.verified_by_id = request.current_user.id
    document.verified_at = datetime.now(timezone.utc)
    db.session.commit()
    return json_response(True, "Document rejected successfully", document.to_dict())


@officer_bp.post("/applications/<application_id>/interview")
@login_required
@role_required("officer")
def schedule_interview(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status not in {"DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED"}:
        return json_response(False, "Documents must be verified before scheduling an interview", status=409)
    complete, _, _ = _required_documents_verified(application)
    if not complete:
        return json_response(False, "All required documents must be verified before scheduling", status=409)
    if Interview.query.filter_by(application_id=application.id, status="SCHEDULED").first():
        return json_response(False, "An active interview already exists for this application", status=409)
    schedule, _, error = _parse_schedule(request.get_json(silent=True) or {})
    if error:
        return json_response(False, error, status=400)
    scheduled_date, scheduled_time, location, mode = schedule
    interview = Interview(application_id=application.id, officer_id=request.current_user.id, scheduled_date=scheduled_date, scheduled_time=scheduled_time, location=location, interview_mode=mode, officer_remarks=str((request.get_json(silent=True) or {}).get("officer_remarks", "")).strip() or None)
    application.status = "INTERVIEW_SCHEDULED"
    db.session.add(interview)
    db.session.commit()
    return json_response(True, "Interview scheduled successfully", interview.to_dict(), status=201)


@officer_bp.get("/applications/<application_id>/interview")
@login_required
@role_required("officer")
def get_interview(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    interview = _interview(application)
    if not interview:
        return json_response(False, "Interview not found", status=404)
    return json_response(True, "Interview retrieved successfully", interview.to_dict())


@officer_bp.put("/applications/<application_id>/interview")
@login_required
@role_required("officer")
def update_interview(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    interview = _interview(application)
    if not interview or interview.status != "SCHEDULED":
        return json_response(False, "Only a scheduled interview can be updated", status=409)
    schedule, _, error = _parse_schedule(request.get_json(silent=True) or {})
    if error:
        return json_response(False, error, status=400)
    interview.scheduled_date, interview.scheduled_time, interview.location, interview.interview_mode = schedule
    interview.officer_remarks = str((request.get_json(silent=True) or {}).get("officer_remarks", "")).strip() or interview.officer_remarks
    db.session.commit()
    return json_response(True, "Interview updated successfully", interview.to_dict())


@officer_bp.post("/applications/<application_id>/interview/complete")
@login_required
@role_required("officer")
def complete_interview(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    interview = _interview(application)
    if not interview or interview.status != "SCHEDULED":
        return json_response(False, "Only a scheduled interview can be completed", status=409)
    data = request.get_json(silent=True) or {}
    outcome = str(data.get("status", "COMPLETED")).upper()
    if outcome not in INTERVIEW_OUTCOMES:
        return json_response(False, "Invalid interview outcome", status=400)
    interview.status = outcome
    interview.officer_remarks = str(data.get("officer_remarks", "")).strip() or interview.officer_remarks
    db.session.commit()
    return json_response(True, "Interview outcome saved successfully", interview.to_dict())


@officer_bp.post("/applications/<application_id>/forward-to-police")
@login_required
@role_required("officer")
def forward_to_police(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status == "POLICE_VERIFICATION":
        return json_response(True, "Application already forwarded to Police", _application_data(application))
    if application.status != "INTERVIEW_SCHEDULED":
        return json_response(False, "Application is not ready to be forwarded to Police", status=409)
    if not Payment.query.filter_by(application_id=application.id, payment_status="SUCCESS").first():
        return json_response(False, "Successful payment is required before forwarding", status=409)
    complete, _, _ = _required_documents_verified(application)
    if not complete:
        return json_response(False, "All required documents must be verified before forwarding", status=409)
    interview = _interview(application)
    if not interview or interview.status != "COMPLETED":
        return json_response(False, "A completed interview is required before forwarding", status=409)
    application.status = "POLICE_VERIFICATION"
    application.forwarded_by_id = request.current_user.id
    application.forwarded_at = datetime.now(timezone.utc)
    db.session.commit()
    return json_response(True, "Application forwarded to Police successfully", _application_data(application))


@officer_bp.post("/applications/<application_id>/reject")
@login_required
@role_required("officer")
def reject_application(application_id):
    application, error_response = _application(application_id)
    if error_response:
        return error_response
    if application.status not in {"SUBMITTED", "DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED"}:
        return json_response(False, "Application cannot be rejected in its current status", status=409)
    reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip()
    if len(reason) < 5:
        return json_response(False, "A meaningful rejection reason is required", status=400)
    application.status = "REJECTED"
    application.rejection_reason = reason
    application.rejected_by_id = request.current_user.id
    application.rejected_at = datetime.now(timezone.utc)
    db.session.commit()
    return json_response(True, "Application rejected successfully", _application_data(application))