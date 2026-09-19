import os
import re
import secrets
import string
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from backend.config import (
    ALLOWED_APPLICATION_TYPES,
    ALLOWED_DOCUMENT_MIME_TYPES,
    ALLOWED_EXTENSIONS,
    ALLOWED_PAYMENT_METHODS,
    APPLICATION_FEE,
    DOCUMENT_REQUIREMENTS,
    MAX_FILE_SIZE_BYTES,
)
from backend.extensions import db
from backend.models.application import Application
from backend.models.document import Document
from backend.models.payment import Payment
from backend.models.user import User
from backend.utils.auth import login_required, role_required

applicant_bp = Blueprint("applicant", __name__)
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s().-]{6,18}[0-9]$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def json_response(success, message, data=None, status=200):
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def _generate_application_id():
    year = datetime.now(timezone.utc).year
    while True:
        suffix = "".join(secrets.choice(string.digits) for _ in range(8))
        application_id = f"PSP{year}{suffix}"
        if not Application.query.filter_by(application_id=application_id).first():
            return application_id


def _generate_transaction_id():
    year = datetime.now(timezone.utc).year
    while True:
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        tx_id = f"TXN-{year}-{suffix}"
        if not Payment.query.filter_by(transaction_id=tx_id).first():
            return tx_id


def _get_own_application_or_404(application_id):
    application = Application.query.filter_by(application_id=application_id).first()
    if not application:
        return None, json_response(False, "Application not found", status=404)
    if application.applicant_id != request.current_user.id:
        return None, json_response(False, "You cannot access another applicant's application", status=403)
    return application, None


def _normalized_dict(data):
    if isinstance(data, dict):
        return data
    return {}


def _validate_required_fields(data, required_fields):
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not str(value).strip()):
            return False
    return True


def _has_valid_phone(value):
    return isinstance(value, str) and bool(PHONE_PATTERN.fullmatch(value.strip()))


def _has_valid_email(value):
    return isinstance(value, str) and bool(EMAIL_PATTERN.fullmatch(value.strip()))


def _required_document_types(application_type):
    return DOCUMENT_REQUIREMENTS.get(application_type, [])


def _current_documents(application):
    return {doc.document_type: doc for doc in application.documents}


def _validate_application_payload(application, data):
    if "status" in data:
        return False, "Status updates are not allowed from the applicant portal"

    if "application_type" in data and data["application_type"] not in ALLOWED_APPLICATION_TYPES:
        return False, "Invalid application type"

    if application.status != "DRAFT":
        return False, "Application can only be updated while it is in draft status"

    return True, None


def _application_is_complete(application):
    personal = _normalized_dict(application.personal_details)
    address = _normalized_dict(application.address_details)
    family = _normalized_dict(application.family_details)
    passport = _normalized_dict(application.passport_details)

    personal_required = [
        "full_name",
        "date_of_birth",
        "gender",
        "place_of_birth",
        "father_name",
        "mother_name",
        "marital_status",
        "nationality",
        "mobile_number",
        "email",
    ]
    if not _validate_required_fields(personal, personal_required):
        return False, "Personal details are incomplete"
    if not _has_valid_email(personal.get("email")):
        return False, "Please provide a valid email in personal details"
    if not _has_valid_phone(personal.get("mobile_number")):
        return False, "Please provide a valid mobile number"

    current_address = _normalized_dict(address.get("current_address"))
    permanent_address = _normalized_dict(address.get("permanent_address"))
    address_required = ["house_number", "street", "area", "city", "district", "state", "pincode"]
    if not _validate_required_fields(current_address, address_required):
        return False, "Current address details are incomplete"
    if not _validate_required_fields(permanent_address, address_required):
        return False, "Permanent address details are incomplete"

    family_required = ["father_name", "mother_name"]
    if not _validate_required_fields(family, family_required):
        return False, "Family details are incomplete"

    if application.application_type == "NEW":
        if "previous_passport_held" not in passport:
            return False, "Previous passport field is required for a new application"
    else:
        required_passport = ["existing_passport_number", "date_of_issue", "date_of_expiry", "place_of_issue", "reason_for_reissue"]
        if not _validate_required_fields(passport, required_passport):
            return False, "Passport details are incomplete for this application type"

    required_docs = _required_document_types(application.application_type)
    uploaded = _current_documents(application)
    missing = [doc_name for doc_name in required_docs if doc_name not in uploaded]
    if missing:
        return False, f"Missing required documents: {', '.join(missing)}"

    return True, None


def _validate_upload_file(file_storage):
    if file_storage is None or file_storage.filename == "":
        return False, "No file uploaded"
    filename = file_storage.filename or ""
    if not filename:
        return False, "No file selected"

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, "Unsupported file type. Allowed: PDF, JPG, JPEG, PNG"

    mime_type = file_storage.mimetype or ""
    if mime_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        return False, "Invalid MIME type"

    file_storage.seek(0, os.SEEK_END)
    file_size = file_storage.tell()
    file_storage.seek(0)
    if file_size <= 0:
        return False, "Uploaded file is empty"
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, "File is too large. Maximum size is 5MB"

    sample = file_storage.read(512)
    file_storage.seek(0)
    if sample[:2] in {b"MZ", b"PK", b"#!", b"<P", b"<?"}:
        return False, "Executable or unsupported content detected"

    return True, {"filename": filename, "size": file_size, "mime_type": mime_type}


@applicant_bp.get("/applications")
@login_required
@role_required("applicant")
def list_applications():
    applications = Application.query.filter_by(applicant_id=request.current_user.id).order_by(Application.created_at.desc()).all()
    payload = [application.to_dict() for application in applications]
    return json_response(True, "Applications retrieved successfully", payload)


@applicant_bp.post("/applications")
@login_required
@role_required("applicant")
def create_application():
    data = request.get_json(silent=True) or {}
    application_type = str(data.get("application_type", "")).upper()
    if application_type not in ALLOWED_APPLICATION_TYPES:
        return json_response(False, "Please select a valid passport application type", status=400)

    application = Application(
        application_id=_generate_application_id(),
        applicant_id=request.current_user.id,
        application_type=application_type,
        status="DRAFT",
        personal_details={},
        address_details={},
        family_details={},
        passport_details={},
    )
    db.session.add(application)
    db.session.commit()
    return json_response(True, "Application created successfully", application.to_dict(), status=201)


@applicant_bp.get("/applications/<application_id>")
@login_required
@role_required("applicant")
def get_application(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response
    return json_response(True, "Application retrieved successfully", application.to_dict())


@applicant_bp.put("/applications/<application_id>")
@login_required
@role_required("applicant")
def update_application(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response

    data = request.get_json(silent=True) or {}
    valid, message = _validate_application_payload(application, data)
    if not valid:
        return json_response(False, message, status=400)

    for key in ["personal_details", "address_details", "family_details", "passport_details"]:
        if key in data and isinstance(data[key], dict):
            current_value = getattr(application, key) or {}
            current_value.update(data[key])
            setattr(application, key, current_value)

    if "application_type" in data:
        application.application_type = str(data["application_type"]).upper()

    db.session.commit()
    return json_response(True, "Application updated successfully", application.to_dict())


@applicant_bp.delete("/applications/<application_id>")
@login_required
@role_required("applicant")
def delete_application(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response
    if application.status != "DRAFT":
        return json_response(False, "Only draft applications can be deleted", status=409)
    db.session.delete(application)
    db.session.commit()
    return json_response(True, "Application deleted successfully")


@applicant_bp.post("/applications/<application_id>/submit")
@login_required
@role_required("applicant")
def submit_application(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response

    payload = request.get_json(silent=True) or {}
    confirmation = bool(payload.get("confirmation", False))
    if not confirmation:
        return json_response(False, "You must confirm the information before submitting", status=400)

    if application.status == "SUBMITTED":
        return json_response(True, "Application already submitted", application.to_dict())

    if application.status not in {"DRAFT"}:
        return json_response(False, "This application cannot be submitted in its current status", status=400)

    valid, message = _application_is_complete(application)
    if not valid:
        return json_response(False, message, status=400)

    successful_payment = Payment.query.filter_by(application_id=application.id, payment_status="SUCCESS").order_by(Payment.created_at.desc()).first()
    if not successful_payment:
        return json_response(False, "Payment must be successful before the application can be submitted", status=400)

    application.status = "SUBMITTED"
    application.submitted_at = datetime.now(timezone.utc)
    db.session.commit()
    return json_response(True, "Application submitted successfully", application.to_dict())


@applicant_bp.post("/applications/<application_id>/documents")
@login_required
@role_required("applicant")
def upload_document(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response

    if application.status != "DRAFT":
        return json_response(False, "Documents can only be updated while the application is in draft", status=400)

    uploaded_file = request.files.get("document")
    doc_type = request.form.get("document_type", "").strip()
    if not doc_type:
        return json_response(False, "Document type is required", status=400)

    valid, details = _validate_upload_file(uploaded_file)
    if not valid:
        return json_response(False, details, status=400 if details not in {"File is too large. Maximum size is 5MB"} else 413)

    allowed_doc_types = set()
    for item in _required_document_types(application.application_type):
        allowed_doc_types.add(item)
    for existing_doc in application.documents:
        allowed_doc_types.add(existing_doc.document_type)
    if doc_type not in allowed_doc_types:
        return json_response(False, "This document type is not valid for this application", status=400)

    upload_dir = current_app.config.get("UPLOAD_FOLDER", os.path.join(current_app.root_path, "uploads", "documents"))
    os.makedirs(upload_dir, exist_ok=True)
    original_name = secure_filename(uploaded_file.filename)
    stored_name = secure_filename(f"{application.application_id}-{doc_type}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}{os.path.splitext(original_name)[1].lower()}")
    file_path = os.path.join(upload_dir, stored_name)
    uploaded_file.save(file_path)

    existing = Document.query.filter_by(application_id=application.id, document_type=doc_type).first()
    if existing:
        try:
            if os.path.exists(existing.file_path):
                os.remove(existing.file_path)
        except OSError:
            pass
        existing.original_filename = original_name
        existing.stored_filename = stored_name
        existing.file_path = file_path
        existing.mime_type = details["mime_type"]
        existing.file_size = details["size"]
        existing.verification_status = "PENDING"
        existing.rejection_reason = None
        existing.uploaded_at = datetime.now(timezone.utc)
        db.session.add(existing)
        document_record = existing
    else:
        document_record = Document(
            application_id=application.id,
            document_type=doc_type,
            original_filename=original_name,
            stored_filename=stored_name,
            file_path=file_path,
            mime_type=details["mime_type"],
            file_size=details["size"],
            verification_status="PENDING",
            rejection_reason=None,
        )
        db.session.add(document_record)

    db.session.commit()
    return json_response(True, "Document uploaded successfully", document_record.to_dict(), status=201)


@applicant_bp.get("/applications/<application_id>/documents")
@login_required
@role_required("applicant")
def list_documents(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response
    return json_response(True, "Documents retrieved successfully", [document.to_dict() for document in application.documents])


@applicant_bp.delete("/applications/<application_id>/documents/<document_id>")
@login_required
@role_required("applicant")
def delete_document(application_id, document_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response

    document = Document.query.filter_by(id=document_id, application_id=application.id).first()
    if not document:
        return json_response(False, "Document not found", status=404)

    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except OSError:
            pass
    db.session.delete(document)
    db.session.commit()
    return json_response(True, "Document deleted successfully")


@applicant_bp.post("/applications/<application_id>/payment")
@login_required
@role_required("applicant")
def process_payment(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response

    if application.status == "SUBMITTED":
        payment = Payment.query.filter_by(application_id=application.id, payment_status="SUCCESS").order_by(Payment.created_at.desc()).first()
        if payment:
            return json_response(True, "Payment already successful", payment.to_dict())

    data = request.get_json(silent=True) or {}
    payment_method = str(data.get("payment_method", "")).strip()
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        return json_response(False, "Please select a valid payment method", status=400)

    if application.status not in {"DRAFT", "SUBMITTED"}:
        return json_response(False, "Payment cannot be processed in the current application status", status=400)

    valid, message = _application_is_complete(application)
    if not valid:
        return json_response(False, message, status=400)

    existing_payment = Payment.query.filter_by(application_id=application.id).order_by(Payment.created_at.desc()).first()
    if existing_payment and existing_payment.payment_status == "SUCCESS":
        return json_response(True, "Payment already successful", existing_payment.to_dict())

    transaction_id = _generate_transaction_id()
    payment = Payment(
        application_id=application.id,
        transaction_id=transaction_id,
        amount=float(APPLICATION_FEE),
        payment_method=payment_method,
        payment_status="SUCCESS",
        paid_at=datetime.now(timezone.utc),
    )
    db.session.add(payment)
    application.status = "SUBMITTED"
    application.submitted_at = application.submitted_at or datetime.now(timezone.utc)
    db.session.commit()
    return json_response(True, "Payment processed successfully", payment.to_dict())


@applicant_bp.get("/applications/<application_id>/payments")
@login_required
@role_required("applicant")
def get_payments(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response
    payments = Payment.query.filter_by(application_id=application.id).order_by(Payment.created_at.desc()).all()
    return json_response(True, "Payments retrieved successfully", [payment.to_dict() for payment in payments])


@applicant_bp.get("/applications/<application_id>/status")
@login_required
@role_required("applicant")
def get_status(application_id):
    application, error_response = _get_own_application_or_404(application_id)
    if error_response is not None:
        return error_response
    timeline = [
        {"status": "Application Created", "completed": True},
        {"status": "Application Submitted", "completed": application.status in {"SUBMITTED", "DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED", "POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Document Verification", "completed": application.status in {"DOCUMENT_VERIFICATION", "INTERVIEW_SCHEDULED", "POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Interview Scheduled", "completed": application.status in {"INTERVIEW_SCHEDULED", "POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Police Verification", "completed": application.status in {"POLICE_VERIFICATION", "APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Approved", "completed": application.status in {"APPROVED", "PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Passport Generated", "completed": application.status in {"PASSPORT_GENERATED", "PASSPORT_DISPATCHED"}},
        {"status": "Passport Dispatched", "completed": application.status == "PASSPORT_DISPATCHED"},
    ]
    return json_response(True, "Status retrieved successfully", {"status": application.status, "timeline": timeline})


@applicant_bp.get("/profile")
@login_required
@role_required("applicant")
def get_profile():
    return json_response(True, "Profile retrieved successfully", request.current_user.to_dict())


@applicant_bp.put("/profile")
@login_required
@role_required("applicant")
def update_profile():
    data = request.get_json(silent=True) or {}
    user = request.current_user

    if "full_name" in data and str(data["full_name"]).strip():
        user.full_name = str(data["full_name"]).strip()
    if "phone" in data and str(data["phone"]).strip():
        if not _has_valid_phone(str(data["phone"])):
            return json_response(False, "Please provide a valid phone number", status=400)
        user.phone = str(data["phone"]).strip()
    if "address" in data and str(data["address"]).strip():
        user.address = str(data["address"]).strip()
    if "email" in data and str(data["email"]).strip() and str(data["email"]).strip().lower() != user.email:
        return json_response(False, "Email cannot be changed from this profile screen", status=400)

    db.session.commit()
    return json_response(True, "Profile updated successfully", user.to_dict())


@applicant_bp.post("/profile/change-password")
@login_required
@role_required("applicant")
def change_password():
    data = request.get_json(silent=True) or {}
    user = request.current_user
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not isinstance(current_password, str) or not user.check_password(current_password):
        return json_response(False, "Current password is incorrect", status=400)
    if not isinstance(new_password, str) or len(new_password) < 8:
        return json_response(False, "New password must be at least 8 characters long", status=400)
    if new_password != confirm_password:
        return json_response(False, "New password and confirm password do not match", status=400)

    user.set_password(new_password)
    db.session.commit()
    return json_response(True, "Password updated successfully")
