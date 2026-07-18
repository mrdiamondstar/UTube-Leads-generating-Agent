"""Subscription plan catalog.

>>> Pricing is defined HERE and nowhere else — edit `amount_cents` to change a
price. Amounts are stored in the smallest currency unit (cents) to avoid float
rounding errors, per standard billing practice.

Default pricing rationale (CIP is a B2B creator-lead intelligence tool):
- Daily   ₹1,000/day   — up to 500 leads; short bursts / evaluation.
- Weekly  ₹5,000/week  — ~₹714/day (~29% cheaper than daily).
- Monthly ₹20,000/mo   — ~₹667/day (~33% cheaper than daily). Best value.

Amounts are in paise (the smallest INR unit): ₹1,000 = 100000 paise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

CURRENCY = "INR"


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    interval: str          # "day" | "week" | "month"
    period_days: int
    amount_cents: int
    tagline: str
    features: list[str] = field(default_factory=list)
    highlight: bool = False
    badge: str | None = None

    @property
    def amount(self) -> float:
        return self.amount_cents / 100.0

    @property
    def per_day_cents(self) -> int:
        return round(self.amount_cents / self.period_days)


# --- The single source of truth for pricing --------------------------------
PLAN_CATALOG: list[Plan] = [
    Plan(
        id="daily",
        name="Daily",
        interval="day",
        period_days=1,
        amount_cents=100000,  # ₹1,000 / day
        tagline="Up to 500 leads for a single day.",
        features=[
            "Full platform access for 24 hours",
            "Up to 500 leads per day",
            "Explainable lead scoring",
            "Excel export",
            "Email support",
        ],
    ),
    Plan(
        id="monthly",
        name="Monthly",
        interval="month",
        period_days=30,
        amount_cents=2000000,  # ₹20,000 / month
        tagline="Best value for ongoing prospecting.",
        features=[
            "Everything in Weekly",
            "30 days of full access",
            "Priority discovery queue",
            "CRM sync (coming soon)",
            "Priority support",
        ],
        highlight=True,
        badge="Most popular",
    ),
    Plan(
        id="weekly",
        name="Weekly",
        interval="week",
        period_days=7,
        amount_cents=500000,  # ₹5,000 / week
        tagline="A full week of prospecting.",
        features=[
            "Everything in Daily",
            "7 days of full access",
            "Saved searches & history",
            "Scheduled discovery",
            "Email support",
        ],
    ),
]

# Display order for the pricing page (Daily · Monthly(highlight) · Weekly keeps
# the popular plan centered).
PLAN_DISPLAY_ORDER = ["daily", "monthly", "weekly"]

_BY_ID = {p.id: p for p in PLAN_CATALOG}


def get_plan(plan_id: str) -> Plan | None:
    return _BY_ID.get(plan_id)


def list_plans() -> list[Plan]:
    return [_BY_ID[pid] for pid in PLAN_DISPLAY_ORDER if pid in _BY_ID]
