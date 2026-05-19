"""
Helpers to avoid leaking secrets or internal details in API responses.
"""

from __future__ import annotations

from django.conf import settings


def public_error_payload(
    message: str,
    *,
    status_code: int,
    code: str | None = None,
    detail=None,
) -> dict:
    """
    Build a safe JSON error body for clients.
    Internal `detail` is only included when DEBUG is True.
    """
    payload: dict = {
        "error": message,
        "status": status_code,
    }
    if code:
        payload["code"] = code
    if detail is not None and getattr(settings, "DEBUG", False):
        payload["detail"] = detail
    return payload


def sanitize_flag_detail(detail: str) -> str:
    """Strip content that should not appear in user-visible flags."""
    blocked = (
        "api_key", "apikey", "password", "secret", "token",
        "GNEWS_", "GOOGLE_FACTCHECK", "DB_", "REDIS_",
        "traceback", "Exception", "C:\\", "/home/",
    )
    lowered = detail.lower()
    if any(b.lower() in lowered for b in blocked):
        return "An internal processing issue occurred."
    return detail
