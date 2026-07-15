"""Pure, unit-testable metric + scoring functions (no I/O).

Kept free of DB/network so the business logic can be tested in isolation and
reused by the performance & scoring agents.
"""
from __future__ import annotations

import math

# Empirically-motivated baseline: a "healthy" channel accrues roughly this many
# lifetime views per subscriber. Below `underperformance_ratio` of this, we treat
# the channel as underperforming for its audience size -> a sales opportunity.
HEALTHY_VIEWS_PER_SUB = 150.0


def views_per_subscriber(view_count: int, subscriber_count: int) -> float:
    if subscriber_count <= 0:
        return 0.0
    return view_count / subscriber_count


def avg_views_per_video(view_count: int, video_count: int) -> float:
    if video_count <= 0:
        return 0.0
    return view_count / video_count


def expected_views(subscriber_count: int) -> float:
    return subscriber_count * HEALTHY_VIEWS_PER_SUB


def performance_ratio(view_count: int, subscriber_count: int) -> float:
    """Actual views / expected views. <1 means below the healthy baseline."""
    expected = expected_views(subscriber_count)
    if expected <= 0:
        return 0.0
    return view_count / expected


def compute_metrics(view_count: int, subscriber_count: int, video_count: int) -> dict:
    return {
        "views_per_subscriber": round(views_per_subscriber(view_count, subscriber_count), 2),
        "avg_views_per_video": round(avg_views_per_video(view_count, video_count), 2),
        "performance_ratio": round(performance_ratio(view_count, subscriber_count), 3),
        "subscriber_count": subscriber_count,
    }


def is_underperforming(view_count: int, subscriber_count: int, threshold_ratio: float) -> bool:
    return performance_ratio(view_count, subscriber_count) < threshold_ratio


# --------------------------------------------------------------------------
# Explainable lead scoring: weighted 0-100 with per-feature contributions.
# --------------------------------------------------------------------------
# Each feature returns a 0..1 "strength". Weights sum to 1.0.
_WEIGHTS = {
    "opportunity_gap": 0.40,  # how far below baseline (bigger gap = bigger upside)
    "audience_size": 0.25,    # larger audience = more valuable if converted
    "reachability": 0.20,     # public contact/website/socials available
    "content_volume": 0.15,   # active channel with enough content to work with
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _opportunity_gap_strength(ratio: float) -> float:
    # ratio=1 (at baseline) -> 0 opportunity; ratio=0 -> full opportunity.
    return _clamp01(1.0 - ratio)


def _audience_size_strength(subs: int) -> float:
    # log-scaled: 1k subs ~0.3, 100k ~0.66, 1M ~0.86.
    if subs <= 0:
        return 0.0
    return _clamp01(math.log10(subs) / 7.0)


def _reachability_strength(has_email: bool, has_website: bool, social_count: int) -> float:
    score = 0.0
    if has_email:
        score += 0.5
    if has_website:
        score += 0.3
    score += min(social_count, 4) * 0.05
    return _clamp01(score)


def _content_volume_strength(video_count: int) -> float:
    # Saturates around ~200 videos.
    return _clamp01(video_count / 200.0)


def score_lead(
    *,
    subscriber_count: int,
    view_count: int,
    video_count: int,
    has_email: bool,
    has_website: bool,
    social_count: int,
    performance_ratio_value: float,
) -> dict:
    """Return an explainable score dict: score(0-100), confidence, category, contributions."""
    features = {
        "opportunity_gap": _opportunity_gap_strength(performance_ratio_value),
        "audience_size": _audience_size_strength(subscriber_count),
        "reachability": _reachability_strength(has_email, has_website, social_count),
        "content_volume": _content_volume_strength(video_count),
    }

    contributions: dict[str, dict] = {}
    total = 0.0
    for name, strength in features.items():
        weight = _WEIGHTS[name]
        contribution = strength * weight * 100.0
        total += contribution
        contributions[name] = {
            "strength": round(strength, 3),
            "weight": weight,
            "contribution": round(contribution, 2),
        }

    score = round(total, 2)

    # Confidence: higher when we have contact data and a non-trivial audience.
    confidence = round(
        _clamp01(0.4 + 0.3 * features["reachability"] + 0.3 * features["audience_size"]), 3
    )

    if score >= 70:
        category = "hot"
    elif score >= 45:
        category = "warm"
    elif score >= 25:
        category = "cold"
    else:
        category = "disqualified"

    top = max(contributions.items(), key=lambda kv: kv[1]["contribution"])[0]
    reasoning = (
        f"Score {score}/100 ({category}). Largest driver: {top} "
        f"(+{contributions[top]['contribution']} pts). "
        f"Performance ratio {round(performance_ratio_value, 2)} vs healthy baseline of 1.0."
    )

    return {
        "score": score,
        "confidence": confidence,
        "category": category,
        "feature_contributions": contributions,
        "reasoning": reasoning,
    }
