"""Unit tests for the pure metric + scoring logic."""
from __future__ import annotations

from app.agents import metrics


def test_performance_ratio_baseline():
    # Exactly at the healthy baseline -> ratio 1.0
    subs = 1000
    views = int(subs * metrics.HEALTHY_VIEWS_PER_SUB)
    assert metrics.performance_ratio(views, subs) == 1.0


def test_underperformance_flag():
    subs = 100_000
    # Only 10 views/sub -> well below 0.5 * 150 baseline.
    assert metrics.is_underperforming(subs * 10, subs, 0.5) is True
    # 200 views/sub -> healthy.
    assert metrics.is_underperforming(subs * 200, subs, 0.5) is False


def test_score_is_bounded_and_explainable():
    result = metrics.score_lead(
        subscriber_count=500_000,
        view_count=5_000_000,  # 10 views/sub -> big opportunity gap
        video_count=300,
        has_email=True,
        has_website=True,
        social_count=3,
        performance_ratio_value=0.07,
    )
    assert 0.0 <= result["score"] <= 100.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["category"] in {"hot", "warm", "cold", "disqualified"}
    # Contributions must sum (approximately) to the score.
    total = sum(c["contribution"] for c in result["feature_contributions"].values())
    assert abs(total - result["score"]) < 0.1


def test_bigger_gap_scores_higher():
    common = dict(
        subscriber_count=100_000,
        view_count=1,
        video_count=100,
        has_email=True,
        has_website=True,
        social_count=2,
    )
    high_gap = metrics.score_lead(**common, performance_ratio_value=0.1)
    low_gap = metrics.score_lead(**common, performance_ratio_value=0.9)
    assert high_gap["score"] > low_gap["score"]
