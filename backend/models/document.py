from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = db.Column(db.String(80), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(80), nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    verification_status = db.Column(db.String(30), nullable=False, default="PENDING")
    rejection_reason = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    verified_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application.id if self.application else None,
            "application_reference": self.application.application_id if self.application else None,
            "document_type": self.document_type,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "verification_status": self.verification_status,
            "rejection_reason": self.rejection_reason,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }
