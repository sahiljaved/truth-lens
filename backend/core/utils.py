"""
Shared utility functions used across the backend.
"""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Clean and normalise extracted text before it is sent to fact-check
    sources:
      - Unicode normalise (NFC)
      - Collapse whitespace
      - Strip leading/trailing whitespace
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 1000) -> str:
    """Truncate text to `max_chars`, appending an ellipsis when cut."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a float to [lo, hi]."""
    return max(lo, min(hi, value))


def build_error_response(message: str, details: dict | None = None) -> dict:
    """Convenience builder for error response bodies."""
    payload = {"error": message}
    if details:
        payload["details"] = details
    return payload
