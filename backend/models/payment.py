from datetime import datetime, timezone

from sqlalchemy.dialects import mysql

from backend.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(mysql.INTEGER(unsigned=True), primary_key=True)
    application_id = db.Column(mysql.INTEGER(unsigned=True), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = db.Column(db.String(40), unique=True, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    payment_method = db.Column(db.String(40), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default="PENDING")
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application.application_id if self.application else None,
            "transaction_id": self.transaction_id,
            "amount": float(self.amount),
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
