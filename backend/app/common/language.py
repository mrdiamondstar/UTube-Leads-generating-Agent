"""Lightweight English-language detection for creator filtering.

Intentionally dependency-free and conservative: a channel's declared
`defaultLanguage` is the strong signal; otherwise we fall back to a script +
common-word heuristic over the title/description. When in doubt we exclude, so
the "English only" filter errs toward precision (fewer non-English creators)
rather than recall.
"""
from __future__ import annotations

import re

# Common English function words + creator-domain words used as a positive signal.
_ENGLISH_WORDS = {
    "the", "and", "to", "of", "a", "an", "in", "is", "it", "you", "that", "for",
    "on", "with", "as", "are", "this", "be", "at", "your", "or", "we", "our",
    "my", "how", "all", "new", "from", "by", "about", "best", "tips", "guide",
    "review", "reviews", "tutorial", "tutorials", "learn", "video", "videos",
    "channel", "subscribe", "watch", "official", "daily", "weekly", "i", "me",
    "us", "they", "what", "when", "where", "why", "which", "who", "get", "make",
    "free", "top", "world", "life", "show", "podcast", "news", "help", "here",
}

_WORD_RE = re.compile(r"[a-z']+")


def is_probably_english(
    title: str | None,
    description: str | None,
    default_language: str | None = None,
) -> bool:
    """Heuristic: is this creator's channel English-language?"""
    # Strong signal: the channel declared its language.
    if default_language:
        return default_language.strip().lower().startswith("en")

    text = f"{title or ''} {description or ''}".strip()
    if not text:
        return False

    # Reject when a meaningful share of letters fall outside the Latin range
    # (Arabic, Cyrillic, CJK, Devanagari, Hebrew, Thai, Greek, …).
    letters = [c for c in text if c.isalpha()]
    if letters:
        non_latin = sum(1 for c in letters if ord(c) > 0x02AF)
        if non_latin / len(letters) > 0.15:
            return False

    # Require at least one common English word (distinguishes English from other
    # Latin-script languages like Spanish/French/Portuguese/German).
    words = _WORD_RE.findall(text.lower())
    return any(w in _ENGLISH_WORDS for w in words)
