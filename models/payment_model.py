# models/payment_model.py
"""
Payment models:
- PaymentPydantic: data validation for service & webhooks
- PaymentORM: SQLAlchemy mapping for Postgres
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class PaymentPydantic(BaseModel):
    payment_id: str                # razorpay payment id or manual id
    user_id: int
    amount: float
    currency: str = "INR"
    method: str                     # razorpay / manual / upi / other
    status: str                     # success / pending / failed
    plan_duration_days: Optional[int] = None
    meta: Optional[dict] = None
    date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class PaymentORM(Base):
    __tablename__ = "payments"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    payment_id = sa.Column(sa.String(128), unique=True, index=True, nullable=False)
    user_id = sa.Column(sa.BigInteger, index=True, nullable=False)
    amount = sa.Column(sa.Numeric(10, 2), nullable=False)
    currency = sa.Column(sa.String(8), default="INR", nullable=False)
    method = sa.Column(sa.String(64), nullable=False)
    status = sa.Column(sa.String(32), nullable=False)
    plan_duration_days = sa.Column(sa.Integer, nullable=True)
    meta = sa.Column(sa.JSON, nullable=True)
    date = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def to_pydantic(self) -> PaymentPydantic:
        return PaymentPydantic(
            payment_id=self.payment_id,
            user_id=self.user_id,
            amount=float(self.amount),
            currency=self.currency,
            method=self.method,
            status=self.status,
            plan_duration_days=self.plan_duration_days,
            meta=self.meta or {},
            date=self.date,
    )
