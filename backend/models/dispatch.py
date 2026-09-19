from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Dispatch(db.Model):
    __tablename__ = "dispatches"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(
        mysql.INTEGER(unsigned=True),
        db.ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    passport_id = db.Column(
        mysql.INTEGER(unsigned=True),
        db.ForeignKey("passports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    dispatched_by_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False, index=True)
    dispatch_date = db.Column(db.DateTime(timezone=True), nullable=False)
    courier_name = db.Column(db.String(120), nullable=False)
    tracking_number = db.Column(db.String(120), nullable=False)
    delivery_method = db.Column(db.String(40), nullable=False)
    dispatch_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = db.relationship("Application", back_populates="dispatch")
    passport = db.relationship("Passport", back_populates="dispatch")
    dispatched_by = db.relationship("User", foreign_keys=[dispatched_by_id])

    def to_dict(self):
        return {
            "application_id": self.application.application_id if self.application else None,
            "passport_number": self.passport.passport_number if self.passport else None,
            "dispatched_by_id": self.dispatched_by_id,
            "dispatched_by_name": self.dispatched_by.full_name if self.dispatched_by else None,
            "dispatch_date": self.dispatch_date.isoformat() if self.dispatch_date else None,
            "courier_name": self.courier_name,
            "tracking_number": self.tracking_number,
            "delivery_method": self.delivery_method,
            "dispatch_remarks": self.dispatch_remarks,
            "current_status": self.application.status if self.application else "PASSPORT_DISPATCHED",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }