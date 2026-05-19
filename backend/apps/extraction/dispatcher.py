"""
Extraction dispatcher.

Single entry point used by the Celery pipeline (and tests) to route an
Upload to the correct extractor without hardcoding the branching logic
everywhere.

Usage
─────
    from apps.extraction.dispatcher import dispatch

    result = dispatch(upload)   # returns ExtractionOutput
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.conf import settings

from apps.verifier.models import Upload
from .exceptions import ExtractionError
from .ocr import extract_text_from_image, OCRResult
from .speech import extract_text_from_video, STTResult

logger = logging.getLogger(__name__)


@dataclass
class ExtractionOutput:
    """
    Unified result returned by `dispatch`, regardless of the extraction method
    used.  The caller never needs to know whether OCR or STT was involved.
    """
    text: str
    word_count: int
    processing_time_ms: int
    method: str                            # "ocr" | "stt" | "passthrough"
    flags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # Method-specific metadata


def dispatch(upload: Upload) -> ExtractionOutput:
    """
    Route the upload to the appropriate extractor and return a normalised
    ExtractionOutput.

    For text uploads the content is passed through directly (no I/O cost).
    For image uploads pytesseract OCR is used.
    For video uploads ffmpeg + Whisper STT is used.

    Raises:
        ExtractionError subclasses on failure (caller decides how to handle).
    """
    if upload.file_type == Upload.FileType.TEXT:
        return _passthrough(upload)

    if upload.file_type == Upload.FileType.IMAGE:
        return _run_ocr(upload)

    if upload.file_type == Upload.FileType.VIDEO:
        return _run_stt(upload)

    raise ExtractionError(
        f"Unknown file_type '{upload.file_type}'.",
        detail=f"upload_id={upload.id}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Private dispatchers
# ──────────────────────────────────────────────────────────────────────────────

def _passthrough(upload: Upload) -> ExtractionOutput:
    text = upload.raw_text.strip()
    return ExtractionOutput(
        text=text,
        word_count=len(text.split()),
        processing_time_ms=0,
        method="passthrough",
    )


def _run_ocr(upload: Upload) -> ExtractionOutput:
    if not upload.file:
        raise ExtractionError(
            "No file attached to this image upload.",
            detail=f"upload_id={upload.id}",
        )

    logger.info("Dispatching OCR for upload %s", upload.id)
    result: OCRResult = extract_text_from_image(upload.file.path)

    return ExtractionOutput(
        text=result.text,
        word_count=result.word_count,
        processing_time_ms=result.processing_time_ms,
        method="ocr",
        flags=result.flags,
        extra={
            "char_count": result.char_count,
            "psm_used": result.psm_used,
        },
    )


def _run_stt(upload: Upload) -> ExtractionOutput:
    if not upload.file:
        raise ExtractionError(
            "No file attached to this video upload.",
            detail=f"upload_id={upload.id}",
        )

    if not getattr(settings, "ENABLE_VIDEO_STT", True):
        raise ExtractionError(
            "Video upload is not supported in the hosted environment. "
            "Use text or an image instead.",
            detail="ENABLE_VIDEO_STT=False",
        )

    logger.info("Dispatching STT for upload %s", upload.id)
    result: STTResult = extract_text_from_video(upload.file.path)

    return ExtractionOutput(
        text=result.transcription,
        word_count=result.word_count,
        processing_time_ms=result.processing_time_ms,
        method="stt",
        flags=result.flags,
        extra={
            "language": result.language,
            "duration_seconds": result.duration_seconds,
            "segments": result.segments,
            "model_size": result.model_size,
        },
    )
