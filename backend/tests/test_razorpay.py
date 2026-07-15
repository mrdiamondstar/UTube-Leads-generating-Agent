"""Razorpay billing tests (no real credentials required)."""
from __future__ import annotations

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.billing import razorpay as rzp
from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_config_reports_disabled_without_keys():
    # No RAZORPAY_* env in tests → payments disabled.
    cfg = client.get("/api/v1/billing/config").json()
    assert cfg["enabled"] is False
    assert cfg["provider"] == "razorpay"


def test_checkout_requires_configuration():
    r = client.post(
        "/api/v1/billing/checkout",
        json={"plan_id": "monthly", "email": "buyer@example.com"},
    )
    assert r.status_code == 503  # not configured


def test_verify_rejects_bad_signature():
    r = client.post(
        "/api/v1/billing/verify",
        json={
            "plan_id": "monthly",
            "email": "buyer@example.com",
            "razorpay_order_id": "order_x",
            "razorpay_payment_id": "pay_x",
            "razorpay_signature": "deadbeef",
        },
    )
    assert r.status_code == 400  # signature verification fails (no/invalid secret)


def test_signature_verification_roundtrip(monkeypatch):
    # Point the tracker at a known secret and verify our HMAC matches Razorpay's scheme.
    secret = "test_secret_key"
    settings = get_settings()
    monkeypatch.setattr(settings, "razorpay_key_secret", secret)

    order_id, payment_id = "order_ABC", "pay_XYZ"
    good = hmac.new(
        secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()

    assert rzp.verify_payment_signature(order_id, payment_id, good) is True
    assert rzp.verify_payment_signature(order_id, payment_id, "wrong") is False
