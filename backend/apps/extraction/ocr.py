"""
OCR module — Tesseract integration via pytesseract.

Public API
──────────
    extract_text_from_image(file_path, lang="eng", preprocess=True)
        → OCRResult

    extract_text_from_bytes(image_bytes, ...)
        → OCRResult

Internal flow
─────────────
  1. Open & validate the image with PIL
  2. Preprocess (grayscale → contrast → sharpen → binarise)
  3. Try Tesseract with a ranked list of PSM configurations
  4. Select the result with the most text content
  5. Raise EmptyExtractionError if nothing was found after all attempts
"""

from __future__ import annotations

import io
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, UnidentifiedImageError
from django.conf import settings

from .exceptions import EmptyExtractionError, InvalidImageError, OCREngineError
from .image_preprocessor import preprocess

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Tesseract PSM (Page Segmentation Mode) trial order.
# We try all of them and pick the richest result, so the caller doesn't need
# to know which layout the image uses.
# ──────────────────────────────────────────────────────────────────────────────
_PSM_CONFIGS: list[str] = [
    "--psm 3 --oem 3",   # Fully automatic page segmentation (default)
    "--psm 6 --oem 3",   # Assume a single uniform block of text
    "--psm 11 --oem 3",  # Sparse text — find as much as possible
    "--psm 4 --oem 3",   # Assume a single column of text
    "--psm 1 --oem 3",   # Automatic with OSD
]


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OCRResult:
    text: str
    word_count: int
    char_count: int
    is_empty: bool
    processing_time_ms: int
    psm_used: str
    flags: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Public functions
# ──────────────────────────────────────────────────────────────────────────────

def extract_text_from_image(
    file_path: str,
    lang: str = "",
    preprocess_image: bool = True,
) -> OCRResult:
    """
    Extract text from an image file on disk.

    Args:
        file_path:        Absolute path to the image file.
        lang:             Tesseract language code(s), e.g. "eng", "eng+fra".
                          Falls back to settings.TESSERACT_LANG.
        preprocess_image: Whether to run the preprocessing pipeline.

    Returns:
        OCRResult dataclass.

    Raises:
        InvalidImageError   — file cannot be opened as an image.
        OCREngineError      — Tesseract binary not found / crashed.
        EmptyExtractionError — image contains no detectable text.
    """
    path = Path(file_path)
    if not path.exists():
        raise InvalidImageError(
            "Image file not found.",
            detail=f"Path does not exist: {file_path}",
        )

    try:
        img = Image.open(path)
        img.verify()            # Catches truncated / corrupt files early
        img = Image.open(path)  # Re-open after verify (verify closes the file)
    except UnidentifiedImageError:
        raise InvalidImageError(
            "The uploaded file is not a valid image.",
            detail=f"PIL could not identify image at {file_path}",
        )
    except Exception as exc:
        raise InvalidImageError(
            "Failed to open image.",
            detail=str(exc),
        )

    return _run_ocr(img, lang=lang, preprocess_image=preprocess_image)


def extract_text_from_bytes(
    image_bytes: bytes,
    lang: str = "",
    preprocess_image: bool = True,
) -> OCRResult:
    """
    Extract text from raw image bytes (e.g. from an in-memory upload).
    Accepts the same arguments as `extract_text_from_image`.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        img = Image.open(io.BytesIO(image_bytes))
    except UnidentifiedImageError:
        raise InvalidImageError("The uploaded file is not a valid image.")
    except Exception as exc:
        raise InvalidImageError("Failed to decode image bytes.", detail=str(exc))

    return _run_ocr(img, lang=lang, preprocess_image=preprocess_image)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _run_ocr(
    img: Image.Image,
    lang: str,
    preprocess_image: bool,
) -> OCRResult:
    """Core OCR logic shared by the public entry points."""
    _configure_tesseract()
    effective_lang = lang or getattr(settings, "TESSERACT_LANG", "eng")
    flags: list[str] = []

    start = time.monotonic()

    # ── Preprocess ────────────────────────────────────────────────────────────
    if preprocess_image:
        try:
            img = preprocess(img)
        except Exception as exc:
            logger.warning("Preprocessing failed, using raw image: %s", exc)
            flags.append("PREPROCESSING_SKIPPED")

    # ── OCR with multi-PSM fallback ───────────────────────────────────────────
    best_text = ""
    best_psm = _PSM_CONFIGS[0]

    for psm_config in _PSM_CONFIGS:
        raw = _tesseract_call(img, lang=effective_lang, config=psm_config)
        cleaned = _clean_text(raw)
        if len(cleaned) > len(best_text):
            best_text = cleaned
            best_psm = psm_config
        if len(best_text) > 200:
            # Good enough — skip remaining configs
            break

    elapsed_ms = int((time.monotonic() - start) * 1000)

    # ── Empty text guard ──────────────────────────────────────────────────────
    if not best_text:
        raise EmptyExtractionError(
            "No text could be extracted from this image.",
            detail="All Tesseract PSM configurations returned empty results.",
        )

    word_count = len(best_text.split())
    if word_count < 3:
        flags.append("LOW_TEXT_CONTENT")

    logger.info(
        "OCR complete: %d words, %d chars, psm=%r, %d ms",
        word_count, len(best_text), best_psm, elapsed_ms,
    )

    return OCRResult(
        text=best_text,
        word_count=word_count,
        char_count=len(best_text),
        is_empty=False,
        processing_time_ms=elapsed_ms,
        psm_used=best_psm,
        flags=flags,
    )


def _configure_tesseract() -> None:
    """
    Point pytesseract at the correct Tesseract binary.
    Reads TESSERACT_CMD from Django settings, then common install paths.
    """
    cmd = getattr(settings, "TESSERACT_CMD", "") or ""
    if cmd and Path(cmd).is_file():
        pytesseract.pytesseract.tesseract_cmd = cmd
        return

    for candidate in _tesseract_candidates():
        if Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            return


def _tesseract_candidates() -> list[str]:
    import shutil
    import sys

    found = shutil.which("tesseract")
    if found:
        return [found]

    if sys.platform != "win32":
        return []

    return [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]


def _tesseract_call(img: Image.Image, lang: str, config: str) -> str:
    """
    Thin wrapper around pytesseract.image_to_string that converts library
    exceptions into our own exception hierarchy.
    """
    try:
        return pytesseract.image_to_string(img, lang=lang, config=config)
    except pytesseract.TesseractNotFoundError:
        raise OCREngineError(
            "Tesseract is not installed or not in the system PATH.",
            detail="pytesseract.TesseractNotFoundError raised.",
        )
    except Exception as exc:
        logger.warning("Tesseract call failed with config %r: %s", config, exc)
        return ""   # Let the multi-PSM loop try the next config


def _clean_text(raw: str) -> str:
    """
    Remove Tesseract noise and normalise whitespace.

    - Strip form-feeds and other control characters Tesseract injects
    - Collapse multiple blank lines to a single blank line
    - Strip surrounding whitespace
    """
    if not raw:
        return ""
    # Remove non-printable control chars (except newline/tab)
    text = re.sub(r"[^\S\n\t ]+", " ", raw)
    # Collapse 3+ consecutive newlines → double newline (paragraph separator)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
