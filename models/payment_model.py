# models/payment_model.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PaymentModel(BaseModel):
    payment_id: str
    user_id: int
    amount: float
    currency: str = "INR"
    method: str
    status: str
    plan_duration_days: Optional[int]
    date: datetime = datetime.utcnow()
