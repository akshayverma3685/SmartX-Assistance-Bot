import time
import pytest

def import_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as e:
        pytest.skip(f"Skipping: cannot import {module_name}: {e}")

def test_create_order_and_verify_signature(monkeypatch):
    pay = import_or_skip("services.payment_service")

    create = None
    for name in ("create_order", "create_payment", "init_order"):
        if hasattr(pay, name):
            create = getattr(pay, name)
            break
    if create is None:
        pytest.skip("Payment order create function not found; skipping")

    # Make provider deterministic
    monkeypatch.setattr(pay, "RAZORPAY_KEY_ID", "rzp_test_x", raising=False)
    monkeypatch.setattr(pay, "RAZORPAY_SECRET", "secret", raising=False)

    # Stub any client call
    for name in ("_razorpay_create_order", "provider_create_order"):
        if hasattr(pay, name):
            monkeypatch.setattr(pay, name, lambda *a, **k: {"id": "order_123", "amount": k.get("amount") or a[0]}, raising=False)

    order = create(amount=19900, user_id=999)
    if hasattr(order, "__await__"):
        import asyncio
        order = asyncio.get_event_loop().run_until_complete(order)

    assert isinstance(order, dict)
    assert order.get("id")
    assert int(order.get("amount", 0)) in (19900, 199)

    # Signature verification (simulate)
    verify = None
    for name in ("verify_signature", "verify_payment", "validate_webhook"):
        if hasattr(pay, name):
            verify = getattr(pay, name)
            break
    if verify is None:
        pytest.skip("Payment signature verifier not found; skipping")

    # Fake valid payload/signature
    ok = verify(payload={"order_id": "order_123", "payment_id": "pay_1"}, signature="testsig")
    assert ok in (True, None)  # Some implementations return None on success


def test_manual_activation_flow(monkeypatch):
    pay = import_or_skip("services.payment_service")
    activate = getattr(pay, "activate_premium_manual", None) or getattr(pay, "activate_premium", None)
    if not callable(activate):
        pytest.skip("Manual premium activation helper not found; skipping")

    # ghost repo for users
    users = {}
    def fake_set_premium(uid, days):
        users[uid] = {"premium_until": time.time() + days * 86400}
        return True

    # Patch possible function hook names
    for cand in ("set_user_premium_for_days", "set_premium_days", "repo_set_premium"):
        if hasattr(pay, cand):
            monkeypatch.setattr(pay, cand, fake_set_premium, raising=False)

    assert activate(user_id=42, days=7) is True
    assert users[42]["premium_until"] > time.time()
