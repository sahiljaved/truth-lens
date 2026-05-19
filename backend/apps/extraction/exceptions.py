"""
Domain-specific exceptions for the extraction pipeline.
All exceptions carry a `user_message` that is safe to surface to the API
caller, and an optional `detail` for internal logging.
"""


class ExtractionError(Exception):
    """Base class for all extraction failures."""

    def __init__(self, user_message: str, detail: str = ""):
        self.user_message = user_message
        self.detail = detail or user_message
        super().__init__(self.detail)


# ── OCR ───────────────────────────────────────────────────────────────────────

class InvalidImageError(ExtractionError):
    """Raised when the uploaded file cannot be opened as a valid image."""


class OCREngineError(ExtractionError):
    """Raised when Tesseract is not installed or returns an unexpected error."""


class EmptyExtractionError(ExtractionError):
    """Raised when no text could be extracted from the input."""


# ── Speech-to-Text ────────────────────────────────────────────────────────────

class InvalidVideoError(ExtractionError):
    """Raised when the uploaded file is not a valid/readable video."""


class AudioExtractionError(ExtractionError):
    """Raised when ffmpeg fails to extract audio from the video."""


class NoAudioTrackError(ExtractionError):
    """Raised when the video contains no audio stream."""


class WhisperError(ExtractionError):
    """Raised when the Whisper model fails to transcribe."""
