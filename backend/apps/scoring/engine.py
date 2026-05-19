"""
Confidence scoring engine.

Algorithm
─────────
For each retrieved article:
  1. Count keyword overlap between the claim and the article text.
  2. Award KEYWORD_BONUS × overlap_count (capped at MAX_KEYWORD_BONUS).
  3. If the source is trusted: award TRUSTED_SOURCE_BONUS × credibility_weight.

After all articles are processed:
  - If zero articles matched: apply NO_MATCH_PENALTY.
  - Compute a raw integer score and normalise to [0.0, 1.0] by dividing by
    NORMALISATION_CEILING (the theoretical maximum for 5 perfect articles).

Scoring constants are all in one place here so they are easy to tune.

Public API
──────────
    score = compute(extracted_text, articles)   → ScoringOutput dataclass
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from core.utils import clamp, truncate_text
from apps.fact_check.credibility import is_trusted
from apps.scoring.keywords import extract_keywords, keyword_overlap_count
from apps.scoring.similarity import similarity_to_articles
from apps.scoring.flags import detect_flags
from apps.scoring.summarizer import summarize

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Scoring constants  (tweak here, nowhere else)
# ──────────────────────────────────────────────────────────────────────────────

TRUSTED_SOURCE_BONUS: float = 15.0   # points per trusted-source match
KEYWORD_BONUS: float = 8.0           # points per overlapping keyword
MAX_KEYWORD_BONUS: float = 24.0      # cap per article (3 overlapping keywords)
SOURCE_PRESENCE_BONUS: float = 3.0   # small bonus for non-trusted outlets only
NO_MATCH_PENALTY: float = -15.0      # applied once when zero articles match

# Normalise against a high ceiling so scores stay conservative
NORMALISATION_CEILING: float = 320.0

# Stricter matching — weak overlap no longer yields 100% confidence
MIN_SIMILARITY_THRESHOLD: float = 0.18
MIN_KEYWORD_OVERLAP: int = 2         # at least 2 shared keywords to count as a match
MAX_CONFIDENCE: float = 0.82         # never show 100% from news search alone


# ──────────────────────────────────────────────────────────────────────────────
# Output dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoringOutput:
    confidence_score: float        # [0.0, 1.0]
    verdict: str                   # VerificationResult.Verdict choice
    summary: str
    flags: list[dict]
    matched_articles: list[dict]   # articles that contributed to the score
    raw_score: float
    keyword_count: int


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def compute(extracted_text: str, articles: list[dict], extraction_error: str = None) -> ScoringOutput:
    """
    Compute the confidence score for a claim against a list of articles.

    Args:
        extracted_text: The OCR/STT/plain text extracted from the submission.
        articles:       List of article dicts from the aggregator.

    Returns:
        ScoringOutput dataclass.
    """
    if not extracted_text or not extracted_text.strip():
        if extraction_error:
            return _empty_result(extraction_error)
        return _empty_result("No text was extracted from the submitted content.")

    # ── 1. Keyword extraction ─────────────────────────────────────────────
    keywords = extract_keywords(extracted_text)
    logger.debug("Scoring: %d keywords extracted", len(keywords))

    # ── 2. Inject similarity scores into article dicts ────────────────────
    articles = similarity_to_articles(extracted_text, articles)

    # ── 3. Score each article ─────────────────────────────────────────────
    raw_score: float = 0.0
    matched_articles: list[dict] = []
    trusted_count: int = 0

    for article in articles:
        similarity = article.get("similarity_score", 0.0)
        if similarity < MIN_SIMILARITY_THRESHOLD:
            continue

        article_text = f"{article.get('title', '')} {article.get('description', '')}"
        overlap = keyword_overlap_count(keywords, article_text)
        if overlap < MIN_KEYWORD_OVERLAP and similarity < 0.35:
            continue

        article_score: float = 0.0

        if overlap > 0:
            article_score += min(overlap * KEYWORD_BONUS, MAX_KEYWORD_BONUS)

        source = article.get("source", "")
        cred_weight = article.get("credibility_weight", 0.4)
        if is_trusted(source):
            article_score += TRUSTED_SOURCE_BONUS * cred_weight * similarity
            trusted_count += 1
        else:
            article_score += SOURCE_PRESENCE_BONUS * cred_weight * similarity

        if article_score > 0:
            article["article_score"] = round(article_score, 2)
            raw_score += article_score
            matched_articles.append(article)

    # ── 4. No-match penalty ───────────────────────────────────────────────
    if not matched_articles:
        raw_score += NO_MATCH_PENALTY

    raw_score = max(raw_score, 0.0)

    # ── 5. Normalise (capped — news search cannot prove a claim fully true) ──
    confidence_score = clamp(raw_score / NORMALISATION_CEILING)
    confidence_score = min(confidence_score, MAX_CONFIDENCE)
    confidence_score = round(confidence_score, 4)

    # ── 6. Verdict ────────────────────────────────────────────────────────
    verdict = _determine_verdict(confidence_score, matched_articles, trusted_count)

    # ── 7. Flags ──────────────────────────────────────────────────────────
    flags = detect_flags(
        extracted_text=extracted_text,
        articles=articles,
        matched_count=len(matched_articles),
        trusted_count=trusted_count,
        raw_score=raw_score,
        confidence_score=confidence_score,
    )

    # ── 8. Summary (natural-language via summarizer) ──────────────────────
    summary = summarize(
        extracted_text=extracted_text,
        matched_articles=matched_articles,
        confidence_score=confidence_score,
        verdict=verdict,
        flags=flags,
    )

    logger.info(
        "Scoring complete: score=%.4f verdict=%s matched=%d trusted=%d raw=%.1f",
        confidence_score, verdict, len(matched_articles), trusted_count, raw_score,
    )

    return ScoringOutput(
        confidence_score=confidence_score,
        verdict=verdict,
        summary=summary,
        flags=flags,
        matched_articles=matched_articles,
        raw_score=raw_score,
        keyword_count=len(keywords),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _determine_verdict(score: float, matched: list[dict], trusted_count: int) -> str:
    from apps.verifier.models import VerificationResult as VR

    if not matched:
        return VR.Verdict.UNVERIFIABLE
    # High bar for "likely true" — needs strong score AND trusted corroboration
    if score >= 0.65 and trusted_count >= 2:
        return VR.Verdict.LIKELY_TRUE
    if score >= 0.65 and trusted_count >= 1:
        return VR.Verdict.UNCERTAIN
    if score >= 0.35:
        return VR.Verdict.UNCERTAIN
    return VR.Verdict.LIKELY_FALSE



def _empty_result(reason: str) -> ScoringOutput:
    from apps.verifier.models import VerificationResult as VR

    return ScoringOutput(
        confidence_score=0.0,
        verdict=VR.Verdict.UNVERIFIABLE,
        summary=reason,
        flags=[{"type": "NO_TEXT", "severity": "CRITICAL", "detail": reason}],
        matched_articles=[],
        raw_score=0.0,
        keyword_count=0,
    )
