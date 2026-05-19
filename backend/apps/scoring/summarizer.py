"""
Natural-language summary generator for verification results.

No paid APIs or heavy NLP models are used.  Summaries are built from
structured data (verdict, score, sources, flags, extracted text) using
a context-aware template engine with varied sentence structures so
repeated verifications don't feel robotic.

Public API
──────────
    text = summarize(
        extracted_text   = "...",
        matched_articles = [...],   # article dicts from the aggregator
        confidence_score = 0.82,
        verdict          = "LIKELY_TRUE",
        flags            = [...],
    )
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Verdict sentence banks
# ──────────────────────────────────────────────────────────────────────────────

_OPENERS: dict[str, list[str]] = {
    "LIKELY_TRUE": [
        "This content appears to be accurate.",
        "The submitted content is likely true.",
        "Based on available evidence, this claim seems credible.",
        "The available news coverage supports the accuracy of this content.",
    ],
    "UNCERTAIN": [
        "The accuracy of this content is uncertain.",
        "This content could not be definitively verified.",
        "Evidence around this claim is mixed or incomplete.",
        "We found some coverage, but it is insufficient for a clear verdict.",
    ],
    "LIKELY_FALSE": [
        "This content appears to be inaccurate or misleading.",
        "The submitted claim is likely false based on available evidence.",
        "News coverage contradicts or does not support this content.",
        "This content shows signs of being misleading or unsubstantiated.",
    ],
    "UNVERIFIABLE": [
        "This content could not be verified with available sources.",
        "No corroborating news articles were found for this content.",
        "There is insufficient evidence to make a determination.",
        "We were unable to find supporting coverage for this claim.",
    ],
}

_SCORE_PHRASES: dict[str, list[str]] = {
    "high": [
        "with a strong confidence score of {score}%",
        "supported by a confidence rating of {score}%",
        "achieving a credibility score of {score}%",
    ],
    "medium": [
        "with a moderate confidence score of {score}%",
        "carrying a confidence rating of {score}%",
        "scoring {score}% on our credibility scale",
    ],
    "low": [
        "with a low confidence score of {score}%",
        "only reaching a confidence score of {score}%",
        "scoring just {score}% on the credibility scale",
    ],
}

_SOURCE_INTRODUCTIONS: list[str] = [
    "It matches coverage from {sources}.",
    "Corroborating articles were found from {sources}.",
    "This is supported by reporting from {sources}.",
    "Related coverage was identified at {sources}.",
]

_TRUSTED_SOURCE_NOTES: list[str] = [
    "{n} of the matching source(s) are considered highly credible.",
    "The match includes {n} high-credibility source(s).",
    "{n} trusted outlet(s) reported on this content.",
]

_NO_SOURCE_NOTES: list[str] = [
    "None of the matched sources are considered highly credible news outlets.",
    "No high-credibility sources were found covering this content.",
    "The matching coverage comes from lower-credibility outlets.",
]

_FLAG_NOTES: dict[str, str] = {
    "NO_SOURCES_FOUND":    "No relevant news articles could be retrieved.",
    "NO_MATCH":            "The retrieved articles did not match the content.",
    "UNVERIFIED":          "No trusted news outlets covered this specific claim.",
    "LOW_EVIDENCE":        "The available evidence is very limited.",
    "WEAK_EVIDENCE":       "The evidence base is thin and inconclusive.",
    "SINGLE_SOURCE":       "Only a single source was matched; more coverage is needed.",
    "INSUFFICIENT_CONTENT":"The submitted text was too short for reliable analysis.",
    "HIGH_CONFIDENCE":     "Multiple trusted sources confirm this content.",
}

_CLAIM_PREVIEWS: list[str] = [
    'The analysed content begins: "{preview}".',
    'Regarding the claim: "{preview}".',
    'The submitted text reads: "{preview}".',
]


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def summarize(
    *,
    extracted_text: str,
    matched_articles: list[dict],
    confidence_score: float,
    verdict: str,
    flags: list[dict],
    seed: Optional[int] = None,
) -> str:
    """
    Generate a human-readable summary of the verification result.

    Args:
        extracted_text:   The original claim / extracted content.
        matched_articles: Article dicts that contributed to the score.
        confidence_score: Normalised float in [0.0, 1.0].
        verdict:          One of LIKELY_TRUE | UNCERTAIN | LIKELY_FALSE | UNVERIFIABLE.
        flags:            List of flag dicts from detect_flags().
        seed:             Optional RNG seed for deterministic output (useful in tests).

    Returns:
        Multi-sentence human-readable string.
    """
    rng = random.Random(seed)
    ctx = _build_context(
        extracted_text=extracted_text,
        matched_articles=matched_articles,
        confidence_score=confidence_score,
        verdict=verdict,
        flags=flags,
    )
    return _render(ctx, rng)


# ──────────────────────────────────────────────────────────────────────────────
# Internal: context dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _Context:
    verdict: str
    score_pct: int
    score_band: str           # "high" | "medium" | "low"
    source_names: list[str]   # up to 3 unique source names
    total_sources: int
    trusted_count: int
    has_sources: bool
    claim_preview: str        # first 100 chars of extracted_text
    active_flags: list[str]   # flag types present
    has_critical_flag: bool


def _build_context(
    *,
    extracted_text: str,
    matched_articles: list[dict],
    confidence_score: float,
    verdict: str,
    flags: list[dict],
) -> _Context:
    score_pct = round(confidence_score * 100)

    if score_pct >= 70:
        band = "high"
    elif score_pct >= 40:
        band = "medium"
    else:
        band = "low"

    # Unique source names (preserve insertion order, max 3)
    seen: list[str] = []
    for art in matched_articles:
        name = art.get("source", "").strip()
        if name and name not in seen:
            seen.append(name)
        if len(seen) == 3:
            break

    trusted_count = sum(
        1 for art in matched_articles if art.get("is_trusted", False)
    )

    active_flags = [f.get("type", "") for f in flags]
    has_critical = any(f.get("severity") == "CRITICAL" for f in flags)

    # Claim preview — first sentence or first 100 chars
    preview = _first_sentence(extracted_text)[:100].strip()
    if len(preview) < len(extracted_text[:100].strip()):
        preview += "…"

    return _Context(
        verdict=verdict,
        score_pct=score_pct,
        score_band=band,
        source_names=seen,
        total_sources=len(matched_articles),
        trusted_count=trusted_count,
        has_sources=bool(matched_articles),
        claim_preview=preview,
        active_flags=active_flags,
        has_critical_flag=has_critical,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal: renderer
# ──────────────────────────────────────────────────────────────────────────────

def _render(ctx: _Context, rng: random.Random) -> str:
    sentences: list[str] = []

    # 1. Opening verdict sentence
    opener = rng.choice(_OPENERS.get(ctx.verdict, _OPENERS["UNCERTAIN"]))
    sentences.append(opener)

    # 2. Score phrase (skip for UNVERIFIABLE with 0 sources)
    if ctx.has_sources or ctx.score_pct > 0:
        score_tmpl = rng.choice(_SCORE_PHRASES[ctx.score_band])
        score_phrase = score_tmpl.format(score=ctx.score_pct)
        # Attach to last sentence rather than a standalone sentence
        sentences[-1] = sentences[-1].rstrip(".") + f", {score_phrase}."

    # 3. Source sentence
    if ctx.source_names:
        formatted = _format_source_list(ctx.source_names, ctx.total_sources)
        src_tmpl = rng.choice(_SOURCE_INTRODUCTIONS)
        sentences.append(src_tmpl.format(sources=formatted))

    # 4. Trusted source note
    if ctx.has_sources:
        if ctx.trusted_count > 0:
            note_tmpl = rng.choice(_TRUSTED_SOURCE_NOTES)
            sentences.append(note_tmpl.format(n=ctx.trusted_count))
        else:
            sentences.append(rng.choice(_NO_SOURCE_NOTES))

    # 5. Flag notes — emit at most 2 to keep summary concise
    notable_flags = [
        ft for ft in ctx.active_flags
        if ft in _FLAG_NOTES and ft != "HIGH_CONFIDENCE"
    ][:2]
    for ft in notable_flags:
        sentences.append(_FLAG_NOTES[ft])

    # 6. Claim preview (always last, optional)
    if ctx.claim_preview and len(ctx.claim_preview) > 15:
        preview_tmpl = rng.choice(_CLAIM_PREVIEWS)
        sentences.append(preview_tmpl.format(preview=ctx.claim_preview))

    return " ".join(sentences)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _format_source_list(names: list[str], total: int) -> str:
    """Turn ['Reuters', 'BBC News', 'AP News'] + total=5 into a prose list."""
    if not names:
        return "unknown sources"
    displayed = names[:3]
    remainder = total - len(displayed)
    joined = _oxford_join(displayed)
    if remainder > 0:
        joined += f" and {remainder} other{'s' if remainder > 1 else ''}"
    return joined


def _oxford_join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _first_sentence(text: str) -> str:
    """Extract the first sentence from text, falling back to the whole string."""
    text = text.strip()
    match = re.search(r"[.!?]", text)
    if match:
        return text[: match.start() + 1].strip()
    return text
