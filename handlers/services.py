from core.logs import log_info, log_error, log_payment, log_usage

# normal info
log_info("User started bot", user_id=12345, source="handlers.start")

# errors
try:
    1/0
except Exception as e:
    log_error("Crash in handler", user_id=12345, source="handlers.example", meta={"step":"calc"}, exc_info=True)

# payments
log_payment("Razorpay payment captured", user_id=12345, source="payment_service", meta={"amount":199, "order_id":"order_xyz"})

# usage
log_usage("Downloaded file", user_id=12345, source="downloader", meta={"size": 12345678})
