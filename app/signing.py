"""HMAC-SHA256 signing for webhook payloads."""

import hashlib
import hmac


SIGNATURE_HEADER = "X-Webhook-Signature"


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Return hex-encoded HMAC-SHA256 of the payload."""
    return hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()


def verify_signature(payload_bytes: bytes, secret: str, signature: str) -> bool:
    """Constant-time comparison of expected vs provided signature."""
    expected = sign_payload(payload_bytes, secret)
    return hmac.compare_digest(expected, signature)
