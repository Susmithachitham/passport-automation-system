APPLICATION_FEE = 1500

APP_TYPE_OPTIONS = {
    "NEW": "New Passport",
    "RENEWAL": "Passport Renewal",
    "REISSUE": "Passport Reissue",
}

DOCUMENT_REQUIREMENTS = {
    "NEW": [
        "Identity Proof",
        "Address Proof",
        "Date of Birth Proof",
        "Photograph",
        "Signature",
    ],
    "RENEWAL": [
        "Existing Passport",
        "Identity Proof",
        "Address Proof",
        "Photograph",
        "Signature",
    ],
    "REISSUE": [
        "Existing Passport",
        "Identity Proof",
        "Address Proof",
        "Photograph",
        "Signature",
    ],
}

ALLOWED_APPLICATION_TYPES = {"NEW", "RENEWAL", "REISSUE"}
ALLOWED_STATUSES = {
    "DRAFT",
    "SUBMITTED",
    "DOCUMENT_VERIFICATION",
    "INTERVIEW_SCHEDULED",
    "POLICE_VERIFICATION",
    "APPROVED",
    "REJECTED",
    "PASSPORT_GENERATED",
    "PASSPORT_DISPATCHED",
}

VALID_STATUS_TRANSITIONS = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"DOCUMENT_VERIFICATION", "REJECTED"},
    "DOCUMENT_VERIFICATION": {"INTERVIEW_SCHEDULED", "REJECTED"},
    "INTERVIEW_SCHEDULED": {"POLICE_VERIFICATION", "REJECTED"},
    "POLICE_VERIFICATION": {"APPROVED", "REJECTED"},
    "APPROVED": {"PASSPORT_GENERATED"},
    "PASSPORT_GENERATED": {"PASSPORT_DISPATCHED"},
    "REJECTED": set(),
    "PASSPORT_DISPATCHED": set(),
}

ALLOWED_PAYMENT_METHODS = {"UPI", "Debit Card", "Credit Card", "Net Banking"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
