"""
Source credibility registry.

Each entry maps a normalised source name (lowercase, stripped) to a weight
in [0.0, 1.0].  Sources absent from this registry receive UNKNOWN_WEIGHT.

These weights are intentionally conservative — they represent editorial
standards and fact-checking track records, not political alignment.
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Credibility weights
# ──────────────────────────────────────────────────────────────────────────────

CREDIBILITY_MAP: dict[str, float] = {
    # Tier 1 — wire services / major international outlets
    "reuters": 0.97,
    "associated press": 0.97,
    "ap news": 0.97,
    "bbc news": 0.93,
    "bbc": 0.93,
    "the guardian": 0.90,
    "guardian": 0.90,
    "the new york times": 0.88,
    "new york times": 0.88,
    "nyt": 0.88,
    "the washington post": 0.87,
    "washington post": 0.87,
    "the economist": 0.90,
    "bloomberg": 0.88,
    "financial times": 0.88,
    "al jazeera": 0.85,
    "npr": 0.88,
    "pbs": 0.88,
    # Tier 2 — regional / broadcast
    "abc news": 0.82,
    "cbs news": 0.82,
    "nbc news": 0.82,
    "cnn": 0.78,
    "time": 0.83,
    "newsweek": 0.76,
    "the atlantic": 0.82,
    "politico": 0.80,
    "axios": 0.80,
    "vox": 0.78,
    # Tier 3 — fact-check specialists
    "snopes": 0.92,
    "politifact": 0.91,
    "factcheck.org": 0.92,
    "africa check": 0.90,
    "full fact": 0.91,
    "lead stories": 0.85,
    # Science / health
    "nature": 0.95,
    "science": 0.95,
    "the lancet": 0.94,
    "new england journal of medicine": 0.95,
    "nejm": 0.95,
    "who": 0.90,
    "cdc": 0.90,
    # International agencies
    "afp": 0.93,
    "afp fact check": 0.93,
    "dpa": 0.90,
    "efe": 0.85,
    # Encyclopaedic — not used in verification pipeline (too loose for claims)
    "wikipedia": 0.40,
    # Additional outlets commonly seen in DDG results
    "the independent": 0.78,
    "independent": 0.78,
    "sky news": 0.80,
    "deutsche welle": 0.85,
    "dw": 0.85,
    "france 24": 0.82,
    "the hill": 0.76,
    "usa today": 0.78,
    "the verge": 0.76,
    "wired": 0.78,
    "ars technica": 0.80,
    "techcrunch": 0.74,
    "forbes": 0.74,
    "business insider": 0.72,
    "the mirror": 0.62,
    "the sun": 0.55,
    "daily mail": 0.52,
    "breitbart": 0.38,
    "infowars": 0.20,
}

# Weight returned for sources that aren't in the registry
UNKNOWN_WEIGHT: float = 0.40

# Minimum weight to count a source as "trusted" in scoring
TRUSTED_THRESHOLD: float = 0.75


# ──────────────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_weight(source_name: str) -> float:
    """
    Return the credibility weight for a source name.
    Performs a normalised lookup (lowercase, stripped) then falls back to
    UNKNOWN_WEIGHT.
    """
    key = source_name.lower().strip()
    # Exact match first
    if key in CREDIBILITY_MAP:
        return CREDIBILITY_MAP[key]
    # Partial match — useful when GNews returns "Reuters - World" etc.
    for registered, weight in CREDIBILITY_MAP.items():
        if registered in key or key in registered:
            return weight
    return UNKNOWN_WEIGHT


def is_trusted(source_name: str) -> bool:
    """Return True if the source meets the trusted threshold."""
    return get_weight(source_name) >= TRUSTED_THRESHOLD


def enrich_articles(articles: list[dict]) -> list[dict]:
    """
    Inject `credibility_weight` and `is_trusted` into a list of article dicts
    (in-place mutation + return for chaining).
    """
    for article in articles:
        source = article.get("source", "")
        article["credibility_weight"] = get_weight(source)
        article["is_trusted"] = is_trusted(source)
    return articles
