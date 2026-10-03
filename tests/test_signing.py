"""Tests for HMAC-SHA256 signing."""

from app.signing import sign_payload, verify_signature


def test_sign_and_verify():
    payload = b'{"hello": "world"}'
    secret = "my-secret"
    sig = sign_payload(payload, secret)
    assert verify_signature(payload, secret, sig)


def test_wrong_secret_fails():
    payload = b'{"hello": "world"}'
    sig = sign_payload(payload, "correct-secret")
    assert not verify_signature(payload, "wrong-secret", sig)


def test_tampered_payload_fails():
    secret = "my-secret"
    sig = sign_payload(b"original", secret)
    assert not verify_signature(b"tampered", secret, sig)


def test_signature_is_hex_string():
    sig = sign_payload(b"data", "key")
    assert isinstance(sig, str)
    int(sig, 16)  # should not raise – valid hex
    assert len(sig) == 64  # SHA-256 produces 64 hex chars
