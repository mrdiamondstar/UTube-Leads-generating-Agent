"""API tests via FastAPI's TestClient (inline pipeline run, mock provider)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_run_pipeline_then_list_leads():
    r = client.post("/api/v1/pipeline/run", json={"query": "cooking", "max_results": 30})
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["status"] == "done"
    assert run["discovered"] == 30

    leads = client.get("/api/v1/leads?limit=100").json()
    assert len(leads) > 0
    # Sorted by score desc.
    scores = [lead["score"]["score"] for lead in leads]
    assert scores == sorted(scores, reverse=True)

    overview = client.get("/api/v1/overview").json()
    assert overview["total_channels"] == 30
    assert "by_category" in overview


def test_filter_by_category():
    client.post("/api/v1/pipeline/run", json={"query": "fitness", "max_results": 40})
    hot = client.get("/api/v1/leads?category=hot").json()
    for lead in hot:
        assert lead["score"]["category"] == "hot"


def test_lead_detail_returns_channel_score_and_videos():
    client.post("/api/v1/pipeline/run", json={"query": "cars", "max_results": 20})
    leads = client.get("/api/v1/leads?limit=1").json()
    channel_id = leads[0]["channel"]["id"]

    detail = client.get(f"/api/v1/leads/{channel_id}/detail").json()
    assert detail["channel"]["id"] == channel_id
    assert detail["channel"]["country_name"] is not None or detail["channel"]["country"] is None
    assert detail["score"] is not None
    assert "feature_contributions" in detail["score"]
    # Non-excluded channels have recent videos tracked.
    assert isinstance(detail["videos"], list)

    missing = client.get("/api/v1/leads/does-not-exist/detail")
    assert missing.status_code == 404
