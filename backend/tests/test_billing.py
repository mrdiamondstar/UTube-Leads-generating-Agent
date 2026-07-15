"""Billing / subscription API tests."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_plans_listed_with_pricing():
    plans = client.get("/api/v1/billing/plans").json()
    ids = {p["id"] for p in plans}
    assert ids == {"daily", "weekly", "monthly"}
    monthly = next(p for p in plans if p["id"] == "monthly")
    assert monthly["highlight"] is True
    assert monthly["amount_cents"] == 19900
    # Monthly per-day should beat daily per-day (it's the value plan).
    daily = next(p for p in plans if p["id"] == "daily")
    assert monthly["per_day_cents"] < daily["per_day_cents"]


def test_subscribe_creates_active_subscription_with_period_end():
    r = client.post(
        "/api/v1/billing/subscribe",
        json={"plan_id": "weekly", "email": "buyer@example.com"},
    )
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["status"] == "active"
    assert sub["amount_cents"] == 5900
    end = datetime.fromisoformat(sub["current_period_end"])
    start = datetime.fromisoformat(sub["started_at"])
    assert 6 <= (end - start).days <= 7  # weekly ~ 7 days

    listed = client.get(
        "/api/v1/billing/subscriptions?email=buyer@example.com"
    ).json()
    assert any(s["id"] == sub["id"] for s in listed)


def test_subscribe_rejects_unknown_plan():
    r = client.post(
        "/api/v1/billing/subscribe",
        json={"plan_id": "nope", "email": "x@example.com"},
    )
    assert r.status_code == 404


def test_subscribe_validates_email():
    r = client.post(
        "/api/v1/billing/subscribe",
        json={"plan_id": "daily", "email": "not-an-email"},
    )
    assert r.status_code == 422
