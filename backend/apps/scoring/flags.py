"""
Flag detection module.

Analyses the scoring context and emits structured flag dicts:

    {
        "type":     str,   # machine-readable flag identifier
        "severity": str,   # LOW | MEDIUM | HIGH | CRITICAL
        "detail":   str,   # human-readable explanation
    }

Flags are consumed by the response builder to populate the `flags` field
of the VerificationResult.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Flag:
    type: str
    severity: str   # LOW | MEDIUM | HIGH | CRITICAL
    detail: str

    def to_dict(self) -> dict:
        return {"type": self.type, "severity": self.severity, "detail": self.detail}


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def detect_flags(
    *,
    extracted_text: str,
    articles: list[dict],
    matched_count: int,
    trusted_count: int,
    raw_score: float,
    confidence_score: float,
) -> list[dict]:
    """
    Evaluate the scoring context and return a list of flag dicts.

    Args:
        extracted_text:   The claim / content that was submitted.
        articles:         All articles returned by the aggregator.
        matched_count:    Number of articles that contributed a positive score.
        trusted_count:    Number of matched articles from trusted sources.
        raw_score:        Pre-normalisation integer score.
        confidence_score: Normalised float score in [0.0, 1.0].

    Returns:
        List of flag dicts (may be empty).
    """
    flags: list[Flag] = []

    # ── Content / input flags ─────────────────────────────────────────────
    if not extracted_text or len(extracted_text.strip()) < 20:
        flags.append(Flag(
            type="INSUFFICIENT_CONTENT",
            severity="HIGH",
            detail="The submitted text is too short for reliable verification.",
        ))

    # ── Source coverage flags ─────────────────────────────────────────────
    if not articles:
        flags.append(Flag(
            type="NO_SOURCES_FOUND",
            severity="CRITICAL",
            detail="No news articles were found for this content.",
        ))

    elif matched_count == 0:
        flags.append(Flag(
            type="NO_MATCH",
            severity="HIGH",
            detail="None of the retrieved articles matched the submitted content.",
        ))

    elif matched_count == 1:
        flags.append(Flag(
            type="SINGLE_SOURCE",
            severity="MEDIUM",
            detail="Only one article matched. More sources are needed for confidence.",
        ))

    if articles and trusted_count == 0:
        flags.append(Flag(
            type="UNVERIFIED",
            severity="HIGH",
            detail="No matches found in trusted/credible news sources.",
        ))

    # ── Confidence flags ──────────────────────────────────────────────────
    if 0 < confidence_score < 0.30:
        flags.append(Flag(
            type="LOW_EVIDENCE",
            severity="HIGH",
            detail=(
                f"Confidence score is very low ({confidence_score:.0%}). "
                "This content could not be corroborated."
            ),
        ))

    elif 0.30 <= confidence_score < 0.55:
        flags.append(Flag(
            type="WEAK_EVIDENCE",
            severity="MEDIUM",
            detail=(
                f"Confidence score is below threshold ({confidence_score:.0%}). "
                "Evidence is limited or inconclusive."
            ),
        ))

    if confidence_score >= 0.80 and trusted_count >= 2:
        flags.append(Flag(
            type="HIGH_CONFIDENCE",
            severity="LOW",
            detail=(
                f"Strong corroboration found ({confidence_score:.0%} confidence, "
                f"{trusted_count} trusted sources)."
            ),
        ))

    return [f.to_dict() for f in flags]
