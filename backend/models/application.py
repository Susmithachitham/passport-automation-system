from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    applicant_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="DRAFT")
    personal_details = db.Column(db.JSON, default=dict)
    address_details = db.Column(db.JSON, default=dict)
    family_details = db.Column(db.JSON, default=dict)
    passport_details = db.Column(db.JSON, default=dict)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    forwarded_by_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=True)
    forwarded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    rejected_by_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    rejected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    documents = db.relationship("Document", backref="application", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="application", cascade="all, delete-orphan")
    interviews = db.relationship("Interview", backref="application", cascade="all, delete-orphan")
    applicant = db.relationship("User", foreign_keys=[applicant_id], backref="applications")
    police_verification = db.relationship("PoliceVerification", back_populates="application", uselist=False, cascade="all, delete-orphan")
    passport = db.relationship("Passport", back_populates="application", uselist=False, cascade="all, delete-orphan")
    dispatch = db.relationship("Dispatch", back_populates="application", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "applicant_id": self.applicant_id,
            "application_type": self.application_type,
            "status": self.status,
            "personal_details": self.personal_details or {},
            "address_details": self.address_details or {},
            "family_details": self.family_details or {},
            "passport_details": self.passport_details or {},
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "forwarded_at": self.forwarded_at.isoformat() if self.forwarded_at else None,
            "forwarded_by_id": self.forwarded_by_id,
            "rejection_reason": self.rejection_reason,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejected_by_id": self.rejected_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "documents": [doc.to_dict() for doc in self.documents],
            "payments": [payment.to_dict() for payment in self.payments],
            "interviews": [interview.to_dict() for interview in self.interviews],
            "police_verification": self.police_verification.to_dict() if self.police_verification else None,
            "passport": self.passport.to_dict() if self.passport else None,
            "dispatch": self.dispatch.to_dict() if self.dispatch else None,
        }
