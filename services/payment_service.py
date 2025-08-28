# services/payment_service.py
import razorpay
import config
import logging

logger = logging.getLogger("smartx_bot.payment_service")
client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))

def create_order(amount_rupees: float, receipt: str, currency="INR"):
    amount_paise = int(amount_rupees * 100)
    order = client.order.create(dict(amount=amount_paise, currency=currency, receipt=receipt, payment_capture=1))
    return order

def fetch_payment(payment_id: str):
    try:
        return client.payment.fetch(payment_id)
    except Exception as e:
        logger.exception("Failed fetching payment: %s", e)
        return None
