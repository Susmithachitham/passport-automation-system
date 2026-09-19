from datetime import date, datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Passport(db.Model):
    __tablename__ = "passports"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        mysql.INTEGER(unsigned=True),
        db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    passport_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = db.relationship("Application", back_populates="passport")
    dispatch = db.relationship("Dispatch", back_populates="passport", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "application_id": self.application.application_id if self.application else None,
            "passport_number": self.passport_number,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "passport_status": self.application.status if self.application else "PASSPORT_GENERATED",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }