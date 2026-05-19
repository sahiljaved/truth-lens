"""
Build a concise search query from noisy OCR / STT text.
"""

from __future__ import annotations

import re

from apps.scoring.keywords import extract_keywords

# Drop OCR noise tokens and list markers
_NOISE = frozenset({
    "ay", "rumours", "rumors", "circulated", "social", "media",
    "posted", "viral", "claim", "claims", "fake", "news", "image",
    "photo", "screenshot", "text", "reads", "submitted",
})

# Common OCR typos → corrected spelling for search APIs
_TYPO_FIXES = {
    "catastrophy": "catastrophe",
    "vacination": "vaccination",
    "vaccinatlon": "vaccination",
}

# Terms that should appear first in the search query when present
_PRIORITY = (
    "vaccination", "vaccine", "vaccines", "immunization", "immunisation",
    "covid", "measles", "ebola", "pandemic",
)


def build_search_query(extracted_text: str, max_words: int = 12) -> str:
    """
    Turn long / noisy extracted text into a short query for news APIs.
    """
    if not extracted_text or not extracted_text.strip():
        return ""

    text = re.sub(r"\s+", " ", extracted_text.strip())
    keywords = extract_keywords(text, max_keywords=20)
    keywords -= _NOISE

    if keywords:
        fixed = {_TYPO_FIXES.get(k, k) for k in keywords}
        priority = [t for t in _PRIORITY if t in fixed]
        rest = sorted(fixed - set(priority), key=len, reverse=True)
        ordered = (priority + rest)[:max_words]
        return " ".join(ordered)

    # Fallback: first N meaningful words from raw text
    words = [
        w for w in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(w) >= 4 and w not in _NOISE
    ]
    return " ".join(words[:max_words]) if words else text[:150]
