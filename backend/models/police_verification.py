from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class PoliceVerification(db.Model):
    __tablename__ = "police_verifications"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        mysql.INTEGER(unsigned=True),
        db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    police_officer_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False, index=True)
    verification_status = db.Column(db.String(20), nullable=False, default="PENDING")
    verification_date = db.Column(db.DateTime(timezone=True), nullable=True)
    address_verified = db.Column(db.Boolean, nullable=True)
    identity_verified = db.Column(db.Boolean, nullable=True)
    applicant_found = db.Column(db.Boolean, nullable=True)
    criminal_record_found = db.Column(db.Boolean, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = db.relationship("Application", back_populates="police_verification")
    police_officer = db.relationship("User", foreign_keys=[police_officer_id])

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application.application_id if self.application else None,
            "police_officer_id": self.police_officer_id,
            "police_officer_name": self.police_officer.full_name if self.police_officer else None,
            "verification_status": self.verification_status,
            "verification_date": self.verification_date.isoformat() if self.verification_date else None,
            "address_verified": self.address_verified,
            "identity_verified": self.identity_verified,
            "applicant_found": self.applicant_found,
            "criminal_record_found": self.criminal_record_found,
            "remarks": self.remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }