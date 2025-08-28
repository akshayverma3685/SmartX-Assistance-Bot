# models/user_model.py
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class UserModel(BaseModel):
    user_id: int
    username: Optional[str] = None
    plan: str = "free"  # free/premium
    expiry_date: Optional[datetime] = None
    trial_used: bool = False
    joined_date: datetime = Field(default_factory=datetime.utcnow)
    referrals: int = 0
    commands_used: int = 0
    language: str = "en"
