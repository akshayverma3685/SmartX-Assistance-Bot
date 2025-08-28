# services/payment_service.py
import razorpay
import config
import logging

logger = logging.getLogger("smartx_bot.payment_service")
_client = None

def _get_client():
    global _client
    if _client:
        return _client
    if not config.RAZORPAY_KEY_ID or not config.RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay keys not configured")
    _client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
    return _client

def create_order(amount_rupees: float, receipt: str, currency: str = "INR"):
    """
    Create razorpay order. Returns order dict.
    """
    try:
        client = _get_client()
        amount_paise = int(amount_rupees * 100)
        order = client.order.create(dict(amount=amount_paise, currency=currency, receipt=receipt, payment_capture=1))
        return order
    except Exception as e:
        logger.exception("create_order failed: %s", e)
        raise

def fetch_payment(payment_id: str):
    try:
        client = _get_client()
        return client.payment.fetch(payment_id)
    except Exception as e:
        logger.exception("fetch_payment failed: %s", e)
        return None

def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature (if using Razorpay webhooks).
    """
    try:
        client = _get_client()
        return client.utility.verify_webhook_signature(payload_body, signature, secret)
    except Exception as e:
        logger.exception("verify_signature failed: %s", e)
        return False
