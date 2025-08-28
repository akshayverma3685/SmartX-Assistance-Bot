# core/helpers.py
from datetime import datetime, timedelta
import config
import logging

logger = logging.getLogger("smartx_bot.helpers")

def get_expiry_from_days(days: int):
    return datetime.utcnow() + timedelta(days=days)

def is_premium(user_doc: dict) -> bool:
    if not user_doc:
        return False
    expiry = user_doc.get("expiry_date")
    if not expiry:
        return False
    if isinstance(expiry, str):
        # assume ISO str
        from dateutil.parser import parse
        expiry = parse(expiry)
    return expiry > datetime.utcnow()

def add_days_to_user(user_doc: dict, days: int):
    from dateutil.parser import parse
    from datetime import datetime
    if not user_doc:
        return None
    expiry = user_doc.get("expiry_date")
    if not expiry:
        new_expiry = datetime.utcnow() + timedelta(days=days)
    else:
        if isinstance(expiry, str):
            expiry = parse(expiry)
        if expiry < datetime.utcnow():
            new_expiry = datetime.utcnow() + timedelta(days=days)
        else:
            new_expiry = expiry + timedelta(days=days)
    return new_expiry
