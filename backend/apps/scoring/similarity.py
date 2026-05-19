"""
Text similarity module.

Provides fast, dependency-free similarity measures between two text strings.
Used by the scoring engine to rank how closely an article matches the
extracted claim text.

Available measures
──────────────────
- jaccard_similarity    — intersection / union of word sets  (0.0–1.0)
- overlap_coefficient   — intersection / min(|A|, |B|)      (0.0–1.0)
- combined_similarity   — weighted blend of both             (0.0–1.0)
"""

from __future__ import annotations

import re


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def jaccard_similarity(text_a: str, text_b: str) -> float:
    """
    Jaccard similarity between the word sets of two strings.

    Best for: comparing texts of similar length.
    """
    set_a = _word_set(text_a)
    set_b = _word_set(text_b)

    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union else 0.0


def overlap_coefficient(text_a: str, text_b: str) -> float:
    """
    Overlap coefficient — intersection over the smaller set.

    Best for: comparing a short claim against a longer article (avoids
    penalising length differences).
    """
    set_a = _word_set(text_a)
    set_b = _word_set(text_b)

    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    smaller = min(len(set_a), len(set_b))
    return intersection / smaller if smaller else 0.0


def combined_similarity(
    text_a: str,
    text_b: str,
    jaccard_weight: float = 0.4,
    overlap_weight: float = 0.6,
) -> float:
    """
    Weighted blend of Jaccard and Overlap coefficient.

    The default weights favour Overlap (handles short claims vs long articles
    well) while still penalising completely unrelated texts via Jaccard.

    Returns a value in [0.0, 1.0].
    """
    j = jaccard_similarity(text_a, text_b)
    o = overlap_coefficient(text_a, text_b)
    return round(jaccard_weight * j + overlap_weight * o, 4)


def similarity_to_articles(claim_text: str, articles: list[dict]) -> list[dict]:
    """
    Compute `combined_similarity` between `claim_text` and each article in
    `articles`, injecting a `similarity_score` key into each dict.

    Modifies dicts in-place and returns the list for chaining.
    """
    for article in articles:
        article_text = f"{article.get('title', '')} {article.get('description', '')}"
        article["similarity_score"] = combined_similarity(claim_text, article_text)
    return articles


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _word_set(text: str) -> set[str]:
    """Lowercase the text and return the set of alphabetic tokens."""
    if not text:
        return set()
    return set(re.findall(r"[a-zA-Z]{2,}", text.lower()))
