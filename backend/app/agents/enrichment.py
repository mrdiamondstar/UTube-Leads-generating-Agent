"""Public Contact Enrichment Agent.

Extracts ONLY publicly available contact info that creators voluntarily publish
in their channel description / About text: a business email, a website, and
links to their other social profiles. It never scrapes private data or accesses
anything beyond what the YouTube Data API already returns.
"""
from __future__ import annotations

import re

from app.agents.base import Agent, ChannelContext

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"']+", re.IGNORECASE)

# domain -> normalized platform name
_SOCIAL_DOMAINS = {
    "instagram.com": "instagram",
    "instagr.am": "instagram",
    "twitter.com": "x",
    "x.com": "x",
    "tiktok.com": "tiktok",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "fb.me": "facebook",
    "linkedin.com": "linkedin",
    "discord.gg": "discord",
    "discord.com": "discord",
    "t.me": "telegram",
    "telegram.me": "telegram",
    "twitch.tv": "twitch",
    "patreon.com": "patreon",
}
_SKIP_HOSTS = ("youtube.com", "youtu.be")


def _host_of(url: str) -> str:
    host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/")[0].lower()
    return host[4:] if host.startswith("www.") else host


def extract_contacts(text: str | None) -> dict:
    """Return {'public_email', 'website', 'social_links'} parsed from free text."""
    text = text or ""
    email_match = _EMAIL_RE.search(text)
    public_email = email_match.group(0) if email_match else None

    social_links: dict[str, str] = {}
    website: str | None = None

    for raw_url in _URL_RE.findall(text):
        url = raw_url.rstrip(".,);]'\"")
        host = _host_of(url)
        platform = None
        for domain, name in _SOCIAL_DOMAINS.items():
            if host == domain or host.endswith("." + domain):
                platform = name
                break
        if platform:
            social_links.setdefault(platform, url)
        elif not any(s in host for s in _SKIP_HOSTS):
            if website is None:
                website = url

    return {"public_email": public_email, "website": website, "social_links": social_links}


class PublicContactEnrichmentAgent(Agent[list[ChannelContext], list[ChannelContext]]):
    name = "enrichment"

    async def handle(self, payload: list[ChannelContext]) -> list[ChannelContext]:
        enriched = 0
        for ctx in payload:
            raw = ctx.raw
            found = extract_contacts(getattr(raw, "description", ""))
            if not raw.public_email and found["public_email"]:
                raw.public_email = found["public_email"]
            if not raw.website and found["website"]:
                raw.website = found["website"]
            if found["social_links"]:
                # Keep any provider-supplied links, add newly-found ones.
                raw.social_links = {**found["social_links"], **(raw.social_links or {})}
            if raw.public_email or raw.website or raw.social_links:
                enriched += 1
        self.log.info("enriched", total=len(payload), with_contacts=enriched)
        return payload
