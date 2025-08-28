# models/referral_model.py
"""
Referral models:
- ReferralPydantic: validation for referral records
- ReferralORM: SQLAlchemy mapping
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReferralPydantic(BaseModel):
    referrer_id: int
    new_user_id: int
    bonus_days: int = 1
    date: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ReferralORM(Base):
    __tablename__ = "referrals"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    referrer_id = sa.Column(sa.BigInteger, index=True, nullable=False)
    new_user_id = sa.Column(sa.BigInteger, index=True, nullable=False)
    bonus_days = sa.Column(sa.Integer, default=1, nullable=False)
    date = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    # unique constraint to avoid duplicates (db migration should create this)
    __table_args__ = (
        sa.UniqueConstraint("referrer_id", "new_user_id", name="uq_referrer_newuser"),
    )

    def to_pydantic(self) -> ReferralPydantic:
        return ReferralPydantic(
            referrer_id=self.referrer_id,
            new_user_id=self.new_user_id,
            bonus_days=self.bonus_days,
            date=self.date,
  )
