"""Razorpay integration — order creation + signature verification.

Uses the REST API over httpx with HTTP Basic auth (key_id:key_secret) and
verifies signatures with stdlib HMAC, so no extra SDK dependency is required.
All credentials are read from settings (env); nothing is hardcoded.
"""
from __future__ import annotations

import hashlib
import hmac

import httpx

from app.core.config import get_settings

_ORDERS_URL = "https://api.razorpay.com/v1/orders"


def is_configured() -> bool:
    s = get_settings()
    return bool(s.razorpay_key_id and s.razorpay_key_secret)


async def create_order(amount: int, currency: str, receipt: str, notes: dict) -> dict:
    """Create a Razorpay order. `amount` is in the smallest currency unit."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            _ORDERS_URL,
            auth=(s.razorpay_key_id, s.razorpay_key_secret),
            json={
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
                "notes": notes,
                "payment_capture": 1,
            },
        )
        resp.raise_for_status()
        return resp.json()


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify the checkout callback signature: HMAC_SHA256(order_id|payment_id)."""
    s = get_settings()
    if not s.razorpay_key_secret:
        return False
    expected = hmac.new(
        s.razorpay_key_secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook payload against the webhook secret."""
    s = get_settings()
    if not s.razorpay_webhook_secret:
        return False
    expected = hmac.new(
        s.razorpay_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature or "")
