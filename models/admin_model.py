# models/admin_model.py
"""
Admin settings model:
- AdminSettingsPydantic: used by admin panel to read/update settings
- AdminSettingsORM: single-row settings table (key-value JSON) for Postgres
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AdminSettingsPydantic(BaseModel):
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)
    premium_plans: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AdminSettingsORM(Base):
    __tablename__ = "admin_settings"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    owner_id = sa.Column(sa.BigInteger, nullable=True)
    owner_name = sa.Column(sa.String(128), nullable=True)
    social_links = sa.Column(sa.JSON, nullable=True)          # {instagram, youtube, telegram, twitter}
    premium_plans = sa.Column(sa.JSON, nullable=True)         # list of plans
    updated_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    def to_pydantic(self) -> AdminSettingsPydantic:
        return AdminSettingsPydantic(
            owner_id=self.owner_id,
            owner_name=self.owner_name,
            social_links=self.social_links or {},
            premium_plans=self.premium_plans or [],
            updated_at=self.updated_at,
  )
