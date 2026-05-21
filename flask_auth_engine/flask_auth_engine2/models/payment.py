from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from utils.extensions import db
from utils.hash import sha256
from utils.time import utcnow


class PaymentRecord(db.Model):
    """Idempotent payment log to prevent double-processing."""
    __tablename__ = "payment_records"
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    plan = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), default="completed")
    processed_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    raw_payload = db.Column(db.JSON)