"""
Response builder.

Converts a ScoringOutput into the canonical VerificationResult payload that
the API serialiser expects and that gets persisted to the database.

    result_payload = build(scoring_output)

    # result_payload is a dict ready for:
    VerificationResult.objects.update_or_create(
        upload=upload,
        defaults=result_payload,
    )
"""

from __future__ import annotations

from apps.scoring.engine import ScoringOutput


def build(output: ScoringOutput) -> dict:
    """
    Transform a ScoringOutput into the VerificationResult field dict.

    The returned dict maps 1-to-1 to VerificationResult model fields:
        confidence_score, verdict, summary, sources, flags
    """
    return {
        "confidence_score": output.confidence_score,
        "verdict": output.verdict,
        "summary": output.summary,
        "sources": _build_sources(output.matched_articles),
        "flags": output.flags,
    }


def _build_sources(articles: list[dict]) -> list[dict]:
    """
    Strip internal scoring metadata and return only the fields defined in
    the API contract for a source entry:
        { name, url, published_at, snippet, credibility_weight, is_trusted,
          relevance_score, article_score }
    """
    sources = []
    for art in articles:
        sources.append({
            "name": art.get("source", "Unknown"),
            "url": art.get("url", ""),
            "published_at": art.get("published_at", ""),
            "snippet": _snippet(art.get("description", "") or art.get("title", "")),
            "credibility_weight": art.get("credibility_weight", 0.4),
            "is_trusted": art.get("is_trusted", False),
            "similarity_score": art.get("similarity_score", 0.0),
            "article_score": art.get("article_score", 0.0),
            "source_type": art.get("source_type", ""),
        })
    return sources


def _snippet(text: str, max_chars: int = 200) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"
