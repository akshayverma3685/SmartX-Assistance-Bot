# models/log_model.py
"""
Logs models:
- LogPydantic: structured logs for storing usage/events
- LogORM: SQLAlchemy model for Postgres
"""

from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class LogPydantic(BaseModel):
    type: str                    # feature_usage / payment / system / error
    user_id: Optional[int] = None
    action: Optional[str] = None
    details: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class LogORM(Base):
    __tablename__ = "logs"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    type = sa.Column(sa.String(64), nullable=False, index=True)
    user_id = sa.Column(sa.BigInteger, nullable=True, index=True)
    action = sa.Column(sa.String(128), nullable=True)
    details = sa.Column(sa.JSON, nullable=True)
    timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def to_pydantic(self) -> LogPydantic:
        return LogPydantic(
            type=self.type,
            user_id=self.user_id,
            action=self.action,
            details=self.details,
            timestamp=self.timestamp,
        )
