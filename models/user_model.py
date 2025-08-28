# models/user_model.py
"""
User models:
- UserPydantic: pydantic model for validation & service-layer
- UserORM: SQLAlchemy ORM model for Postgres (async)
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# -----------------------
# Pydantic model
# -----------------------
class UserPydantic(BaseModel):
    user_id: int
    username: Optional[str] = None
    plan: str = "free"                # free | premium
    expiry_date: Optional[datetime] = None
    trial_used: bool = False
    joined_date: datetime = Field(default_factory=datetime.utcnow)
    referrals: int = 0
    commands_used: int = 0
    language: str = "en"
    last_active: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# -----------------------
# SQLAlchemy ORM model
# -----------------------
class UserORM(Base):
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.BigInteger, unique=True, index=True, nullable=False)
    username = sa.Column(sa.String(64), nullable=True)
    plan = sa.Column(sa.String(32), default="free", nullable=False)
    expiry_date = sa.Column(sa.DateTime(timezone=True), nullable=True)
    trial_used = sa.Column(sa.Boolean, default=False, nullable=False)
    joined_date = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    referrals = sa.Column(sa.Integer, default=0, nullable=False)
    commands_used = sa.Column(sa.Integer, default=0, nullable=False)
    language = sa.Column(sa.String(8), default="en", nullable=False)
    last_active = sa.Column(sa.DateTime(timezone=True), nullable=True)

    def to_pydantic(self) -> UserPydantic:
        return UserPydantic(
            user_id=self.user_id,
            username=self.username,
            plan=self.plan,
            expiry_date=self.expiry_date,
            trial_used=self.trial_used,
            joined_date=self.joined_date,
            referrals=self.referrals,
            commands_used=self.commands_used,
            language=self.language,
            last_active=self.last_active,
    )
