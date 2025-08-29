# core/security.py
"""
Security helpers:
- password hashing (bcrypt via passlib)
- token signing (itsdangerous) for admin sessions / short tokens
- HMAC signature verifier for webhooks (e.g., Razorpay)
- simple API key check helper
"""

from typing import Optional
import hmac
import hashlib
import os
import logging

from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

import config

logger = logging.getLogger("core.security")

# Password hashing context (bcrypt)
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token signer for short tokens (e.g., confirm links)
_SIGNER_SECRET = getattr(config, "SECRET_KEY", os.getenv("SECRET_KEY", "change_me"))
_SIGNER_SALT = "smartx-signer-salt"
_signer = URLSafeTimedSerializer(_SIGNER_SECRET, salt=_SIGNER_SALT)

# -------------------------
# Password hashing
# -------------------------
def hash_password(password: str) -> str:
    """Hash plaintext password (sync)."""
    return _pwd_ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash (sync)."""
    try:
        return _pwd_ctx.verify(password, hashed)
    except Exception as e:
        logger.debug("verify_password error: %s", e)
        return False

# -------------------------
# Token signing / verification
# -------------------------
def sign_payload(payload: dict) -> str:
    """
    Sign a payload (dict -> string). Suitable for short-lived tokens.
    Note: payload should be JSON-serializable primitives.
    """
    return _signer.dumps(payload)


def unsign_payload(token: str, max_age: Optional[int] = None) -> Optional[dict]:
    """
    Verify token and return payload dict. If invalid/expired returns None.
    max_age in seconds.
    """
    try:
        data = _signer.loads(token, max_age=max_age)
        return data
    except SignatureExpired:
        logger.warning("Token expired")
        return None
    except BadSignature:
        logger.warning("Bad token signature")
        return None
    except Exception as e:
        logger.exception("unsign_payload error: %s", e)
        return None

# -------------------------
# HMAC verifier (webhooks)
# -------------------------
def verify_hmac_signature(secret: str, payload_body: bytes, signature_header: str, algo: str = "sha256") -> bool:
    """
    Verifies HMAC signature. signature_header can be raw hex or prefixed.
    Returns True if signature matches.
    """
    try:
        if not secret:
            logger.debug("No webhook secret configured")
            return False
        mac = hmac.new(secret.encode("utf-8"), payload_body, getattr(hashlib, algo))
        digest = mac.hexdigest()
        # Accept either raw or prefixed forms (like sha256=...)
        sig = signature_header or ""
        if "=" in sig:
            sig = sig.split("=", 1)[1]
        return hmac.compare_digest(digest, sig)
    except Exception as e:
        logger.exception("verify_hmac_signature error: %s", e)
        return False

# -------------------------
# API key helper (simple)
# -------------------------
def is_valid_admin_apikey(provided: str) -> bool:
    """
    Compare provided API key against config ADMIN_API_KEY (timing-safe).
    """
    expected = getattr(config, "ADMIN_API_KEY", None) or os.getenv("ADMIN_API_KEY")
    if not expected:
        return False
    try:
        return hmac.compare_digest(expected, provided)
    except Exception:
        return False
