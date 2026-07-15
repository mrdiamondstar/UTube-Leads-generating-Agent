"""TEST DOUBLE ONLY — deterministic fake provider.

This is NOT production data. It exists solely so the test suite and offline dev
can exercise the pipeline without hitting the live, quota-limited YouTube Data
API. It is selected only when YOUTUBE_PROVIDER=mock; the product default is the
real API (see app/integrations/youtube/api.py).
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from app.domain.schemas import RawChannel, RawVideo
from app.integrations.youtube.base import YouTubeProvider

_COUNTRIES = ["US", "GB", "CA", "DE", "BR", "AU", "FR", "JP", "IN", "NG"]
_CATEGORIES = ["Tech", "Gaming", "Education", "Finance", "Cooking", "Fitness", "Travel"]


def _seed_for(query: str) -> int:
    return int(hashlib.sha256(query.encode()).hexdigest(), 16) % (2**32)


class MockYouTubeProvider(YouTubeProvider):
    async def search_channels(self, query: str, max_results: int = 25) -> list[RawChannel]:
        rng = random.Random(_seed_for(query))
        out: list[RawChannel] = []
        for i in range(max_results):
            subs = rng.choice([1_200, 8_500, 45_000, 120_000, 500_000, 1_200_000])
            underperformer = rng.random() < 0.4
            per_sub = rng.uniform(8, 40) if underperformer else rng.uniform(120, 400)
            views = int(subs * per_sub)
            country = rng.choice(_COUNTRIES)
            category = rng.choice(_CATEGORIES)
            has_email = rng.random() < 0.5
            cid = f"UC{_seed_for(query + str(i)):024d}"[:24]
            out.append(
                RawChannel(
                    youtube_id=cid,
                    title=f"{category} channel {i + 1} · {query}",
                    description=f"A {category.lower()} creator focused on {query}.",
                    country=country,
                    category=category,
                    subscriber_count=subs,
                    view_count=views,
                    video_count=rng.randint(15, 900),
                    uploads_playlist_id=f"UU{cid[2:]}",
                    website=f"https://example-{i}.com" if rng.random() < 0.6 else None,
                    public_email=f"contact{i}@example-{i}.com" if has_email else None,
                    social_links={
                        k: f"https://{k}.com/creator{i}"
                        for k in rng.sample(
                            ["instagram", "x", "tiktok", "linkedin", "facebook"],
                            k=rng.randint(0, 3),
                        )
                    },
                )
            )
        return out

    async def get_recent_videos(
        self, uploads_playlist_id: str, channel_youtube_id: str, max_results: int = 10
    ) -> list[RawVideo]:
        rng = random.Random(_seed_for(uploads_playlist_id))
        now = datetime.now(timezone.utc)
        out: list[RawVideo] = []
        for i in range(max_results):
            views = rng.randint(500, 500_000)
            out.append(
                RawVideo(
                    video_id=f"{_seed_for(uploads_playlist_id + str(i)):011d}"[:11],
                    channel_youtube_id=channel_youtube_id,
                    title=f"Recent video {i + 1}",
                    published_at=now - timedelta(days=i * 7),
                    view_count=views,
                    like_count=int(views * rng.uniform(0.01, 0.06)),
                    comment_count=int(views * rng.uniform(0.001, 0.01)),
                )
            )
        return out
