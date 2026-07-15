"""YouTube integration error types."""
from __future__ import annotations


class YouTubeError(Exception):
    """Base class for YouTube integration errors."""


class QuotaExceededError(YouTubeError):
    """Raised when the daily quota budget is (or would be) exhausted.

    Not retryable — retrying only burns more quota.
    """


class TransientApiError(YouTubeError):
    """Retryable API error (5xx / 429 / network)."""


class ApiKeyMissingError(YouTubeError):
    """Raised when YOUTUBE_API_KEY is not configured."""
