"""Tests for public contact extraction from channel descriptions."""
from __future__ import annotations

from app.agents.enrichment import extract_contacts


def test_extracts_email_website_and_socials():
    desc = (
        "Tech reviews weekly! Business: hello@creator.com\n"
        "Site: https://creatorsite.com\n"
        "Follow me: https://instagram.com/creator and https://www.tiktok.com/@creator\n"
        "Subscribe: https://youtube.com/@creator"
    )
    out = extract_contacts(desc)
    assert out["public_email"] == "hello@creator.com"
    assert out["website"] == "https://creatorsite.com"
    assert out["social_links"]["instagram"].endswith("/creator")
    assert "tiktok" in out["social_links"]
    # The channel's own YouTube link is not treated as a website.
    assert "youtube" not in (out["website"] or "")


def test_handles_empty_and_none():
    assert extract_contacts("") == {
        "public_email": None,
        "website": None,
        "social_links": {},
    }
    assert extract_contacts(None)["public_email"] is None


def test_twitter_and_x_normalize_together():
    out = extract_contacts("me on https://x.com/foo")
    assert out["social_links"]["x"] == "https://x.com/foo"
