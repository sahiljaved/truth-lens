"""
Typed exceptions for the fact-check pipeline.
Each carries a `user_message` (safe to return to the API caller) and a
`detail` string for internal logging.
"""


class FactCheckError(Exception):
    """Base class for all fact-check failures."""

    def __init__(self, user_message: str, detail: str = ""):
        self.user_message = user_message
        self.detail = detail or user_message
        super().__init__(self.detail)


class SourceUnavailableError(FactCheckError):
    """Source API returned a non-retryable HTTP error (4xx other than 429)."""


class RateLimitError(FactCheckError):
    """Source API rate-limit (HTTP 429) was hit."""

    def __init__(self, source: str, retry_after: int = 0):
        self.source = source
        self.retry_after = retry_after
        msg = (
            f"Rate limit reached for '{source}'. "
            + (f"Retry after {retry_after}s." if retry_after else "")
        )
        super().__init__(user_message=msg, detail=msg)


class InvalidAPIKeyError(FactCheckError):
    """API key is missing, invalid, or expired."""


class SearchTimeoutError(FactCheckError):
    """HTTP request to a source timed out."""


class ParseError(FactCheckError):
    """Unexpected response structure from a source."""
