"""
Verification pipeline — can be invoked via Celery task or direct thread call.

Execution order:
  1. Extract text from the Upload via the dispatcher (OCR / STT / passthrough)
  2. Query all fact-check sources in parallel
  3. Compute confidence score & flags
  4. Persist VerificationResult and update Upload.status
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Core pipeline — called by both the Celery task and the thread fallback
# ──────────────────────────────────────────────────────────────────────────────

def execute_pipeline(upload_id: str) -> None:
    """
    Run the full extraction → fact-check → scoring pipeline synchronously.
    Safe to call from a plain thread or a Celery worker.
    """
    from apps.verifier.models import Upload, VerificationResult
    from apps.extraction.dispatcher import dispatch
    from apps.extraction.exceptions import ExtractionError
    from core.utils import normalize_text
    from core.search_query import build_search_query

    try:
        upload = Upload.objects.get(pk=upload_id)
    except Upload.DoesNotExist:
        logger.error("execute_pipeline: Upload %s not found.", upload_id)
        return

    try:
        # ── Step 1: Extract text ──────────────────────────────────────────
        try:
            extraction = dispatch(upload)
            extracted_text = normalize_text(extraction.text)
            extraction_flags = extraction.extra
        except ExtractionError as exc:
            logger.warning(
                "Extraction failed for upload %s: %s", upload_id, exc.detail
            )
            extracted_text = ""
            extraction_flags = {
                "extraction_error": exc.user_message,
                "extraction_failed": True,
            }

        upload.extracted_text = extracted_text
        upload.save(update_fields=["extracted_text", "updated_at"])

        # ── Step 2: Query fact-check sources ─────────────────────────────
        search_query = build_search_query(extracted_text) or extracted_text
        source_results = _query_sources(search_query)

        # ── Step 3: Score ─────────────────────────────────────────────────
        extraction_failed = bool(
            extraction_flags.get("extraction_failed") if extraction_flags else False
        )
        score, verdict, summary, pipeline_flags, processed_sources = _compute_score(
            source_results, extracted_text, extraction_error=extraction_flags.get("extraction_error") if extraction_failed else None
        )

        if extraction_flags and extraction_flags.get("extraction_failed"):
            pipeline_flags.append({
                "type": "EXTRACTION_WARNING",
                "severity": "MEDIUM",
                "detail": "Text could not be fully extracted from this upload.",
            })

        # ── Step 4: Persist result ────────────────────────────────────────
        VerificationResult.objects.update_or_create(
            upload=upload,
            defaults={
                "confidence_score": score,
                "verdict": verdict,
                "summary": summary,
                "sources": processed_sources,   # uses name/snippet/relevance_score keys
                "flags": pipeline_flags,
            },
        )

        upload.status = Upload.Status.COMPLETED
        upload.save(update_fields=["status", "updated_at"])

        logger.info(
            "Verification complete: upload=%s score=%.2f verdict=%s",
            upload_id, score, verdict,
        )

    except Exception as exc:
        logger.exception("Verification failed for upload %s: %s", upload_id, exc)
        try:
            upload.status = Upload.Status.FAILED
            upload.save(update_fields=["status", "updated_at"])
        except Exception:
            pass
        raise


# ──────────────────────────────────────────────────────────────────────────────
# Celery task wrapper (used when Redis + worker are available)
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="tasks.run_verification_pipeline",
)
def run_verification_pipeline(self, upload_id: str):
    try:
        execute_pipeline(upload_id)
    except Exception as exc:
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────────

def _query_sources(text: str) -> list:
    from apps.fact_check.aggregator import search_all_sources
    from apps.fact_check.exceptions import FactCheckError

    if not text:
        return []

    try:
        return search_all_sources(query=text, max_results=5)
    except FactCheckError as exc:
        logger.warning("_query_sources failed: %s", exc.detail)
        return []
    except Exception as exc:
        logger.exception("Unexpected error in _query_sources: %s", exc)
        return []


def _compute_score(source_results: list, extracted_text: str, extraction_error: str = None):
    from apps.scoring.engine import compute
    from apps.scoring.response_builder import build

    output = compute(
        extracted_text=extracted_text,
        articles=source_results,
        extraction_error=extraction_error,
    )
    payload = build(output)

    return (
        payload["confidence_score"],
        payload["verdict"],
        payload["summary"],
        payload["flags"],
        payload["sources"],   # processed with name/snippet/relevance_score keys
    )
