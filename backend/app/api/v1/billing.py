"""Billing / subscription endpoints (Daily / Weekly / Monthly plans)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import razorpay as rzp
from app.billing.plans import CURRENCY, get_plan, list_plans
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.domain.models import Subscription
from app.domain.schemas import (
    BillingConfigOut,
    CheckoutOut,
    CheckoutRequest,
    PlanOut,
    SubscribeRequest,
    SubscriptionOut,
    VerifyPaymentRequest,
)

router = APIRouter()
log = get_logger("billing")


def _new_subscription(plan, email: str, provider: str, payment_ref: str | None) -> Subscription:
    now = datetime.now(timezone.utc)
    return Subscription(
        customer_email=email,
        plan_id=plan.id,
        interval=plan.interval,
        amount_cents=plan.amount_cents,
        currency=CURRENCY,
        status="active",
        provider=provider,
        payment_ref=payment_ref,
        started_at=now,
        current_period_end=now + timedelta(days=plan.period_days),
    )


@router.get("/billing/plans", response_model=list[PlanOut])
async def plans() -> list[PlanOut]:
    return [
        PlanOut(
            id=p.id,
            name=p.name,
            interval=p.interval,
            period_days=p.period_days,
            amount_cents=p.amount_cents,
            amount=p.amount,
            per_day_cents=p.per_day_cents,
            currency=CURRENCY,
            tagline=p.tagline,
            features=p.features,
            highlight=p.highlight,
            badge=p.badge,
        )
        for p in list_plans()
    ]


@router.get("/billing/config", response_model=BillingConfigOut)
async def billing_config() -> BillingConfigOut:
    """Tell the frontend whether live payments (Razorpay) are configured."""
    s = get_settings()
    return BillingConfigOut(
        enabled=rzp.is_configured(),
        key_id=s.razorpay_key_id or None,
        currency=s.razorpay_currency,
    )


@router.post("/billing/subscribe", response_model=SubscriptionOut, status_code=201)
async def subscribe(
    body: SubscribeRequest, session: AsyncSession = Depends(get_session)
) -> Subscription:
    """Demo subscribe (no charge). Used when Razorpay is not configured."""
    plan = get_plan(body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"unknown plan '{body.plan_id}'")
    sub = _new_subscription(plan, body.email, provider="manual", payment_ref=None)
    session.add(sub)
    await session.flush()
    return sub


@router.post("/billing/checkout", response_model=CheckoutOut)
async def create_checkout(body: CheckoutRequest) -> CheckoutOut:
    """Create a Razorpay order for a plan; the frontend opens Razorpay Checkout."""
    plan = get_plan(body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"unknown plan '{body.plan_id}'")
    if not rzp.is_configured():
        raise HTTPException(status_code=503, detail="Payments are not configured")

    s = get_settings()
    order = await rzp.create_order(
        amount=plan.amount_cents,
        currency=s.razorpay_currency,
        receipt=f"cip_{plan.id}_{int(time.time())}",
        notes={"plan_id": plan.id, "email": body.email},
    )
    return CheckoutOut(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=s.razorpay_key_id,
        plan_id=plan.id,
        plan_name=plan.name,
        email=body.email,
    )


@router.post("/billing/verify", response_model=SubscriptionOut, status_code=201)
async def verify_payment(
    body: VerifyPaymentRequest, session: AsyncSession = Depends(get_session)
) -> Subscription:
    """Verify the Razorpay signature and activate the subscription."""
    plan = get_plan(body.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"unknown plan '{body.plan_id}'")
    if not rzp.verify_payment_signature(
        body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature
    ):
        raise HTTPException(status_code=400, detail="Payment verification failed")

    sub = _new_subscription(
        plan, body.email, provider="razorpay", payment_ref=body.razorpay_payment_id
    )
    session.add(sub)
    await session.flush()
    log.info("subscription.paid", plan=plan.id, email=body.email, payment=body.razorpay_payment_id)
    return sub


@router.post("/billing/webhook")
async def razorpay_webhook(request: Request) -> dict:
    """Receive Razorpay webhooks (e.g. payment.captured); verify the signature."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not rzp.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    # Event handling (idempotent upserts) can be added here as needed.
    log.info("razorpay.webhook", bytes=len(body))
    return {"ok": True}


@router.get("/billing/subscriptions", response_model=list[SubscriptionOut])
async def subscriptions(
    email: str | None = None, session: AsyncSession = Depends(get_session)
) -> list[Subscription]:
    stmt = select(Subscription).order_by(Subscription.created_at.desc())
    if email:
        stmt = stmt.where(Subscription.customer_email == email)
    rows = await session.execute(stmt)
    return list(rows.scalars().all())
