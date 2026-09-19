from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    officer_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False, index=True)
    scheduled_date = db.Column(db.Date, nullable=False)
    scheduled_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    interview_mode = db.Column(db.String(30), nullable=False, default="IN_PERSON")
    status = db.Column(db.String(30), nullable=False, default="SCHEDULED")
    officer_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    officer = db.relationship("User", foreign_keys=[officer_id])

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application.application_id if self.application else None,
            "officer_id": self.officer_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "location": self.location,
            "interview_mode": self.interview_mode,
            "status": self.status,
            "officer_remarks": self.officer_remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }