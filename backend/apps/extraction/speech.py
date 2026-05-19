"""
Speech-to-text module — local Whisper + ffmpeg.

Public API
──────────
    extract_text_from_video(file_path, language=None, model_size="small")
        → STTResult

Internal flow
─────────────
  1. Validate the video file exists and is non-empty
  2. Probe audio streams with ffprobe (raises NoAudioTrackError if none)
  3. Extract audio to a 16-kHz mono WAV in a temp directory (ffmpeg)
  4. Load the Whisper model (cached after first load in the process)
  5. Transcribe; collect segments + detected language
  6. Clean up the temp WAV
  7. Return an STTResult dataclass

Design notes
────────────
- The Whisper model is process-level cached so repeated calls in the same
  Celery worker don't reload it from disk every time.
- ffmpeg is invoked via subprocess (no ffmpeg-python dependency) so the
  only extra system requirement is the `ffmpeg` binary on PATH.
- All temp files are deleted even if an exception is raised.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from django.conf import settings

from .exceptions import (
    AudioExtractionError,
    InvalidVideoError,
    NoAudioTrackError,
    WhisperError,
    EmptyExtractionError,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Module-level Whisper model cache
# Key: model_size string  →  Value: loaded whisper.Model
# ──────────────────────────────────────────────────────────────────────────────
_MODEL_CACHE: dict = {}


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class STTResult:
    transcription: str
    language: str
    duration_seconds: float
    segments: list[dict]
    word_count: int
    processing_time_ms: int
    model_size: str
    flags: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Public function
# ──────────────────────────────────────────────────────────────────────────────

def extract_text_from_video(
    file_path: str,
    language: Optional[str] = None,
    model_size: str = "",
) -> STTResult:
    """
    Transcribe speech from a video file.

    Args:
        file_path:   Absolute path to the video file.
        language:    ISO-639-1 language hint (e.g. "en", "fr").
                     Pass None to let Whisper auto-detect.
        model_size:  One of "tiny", "base", "small", "medium", "large".
                     Falls back to settings.WHISPER_MODEL_SIZE (default "small").

    Returns:
        STTResult dataclass.

    Raises:
        InvalidVideoError    — file missing or unreadable.
        NoAudioTrackError    — video has no audio stream.
        AudioExtractionError — ffmpeg failed.
        WhisperError         — Whisper model failed.
        EmptyExtractionError — transcription is blank.
    """
    path = Path(file_path)
    if not path.exists() or path.stat().st_size == 0:
        raise InvalidVideoError(
            "Video file not found or is empty.",
            detail=f"Path: {file_path}",
        )

    effective_model = model_size or getattr(settings, "WHISPER_MODEL_SIZE", "small")
    effective_lang = language or getattr(settings, "WHISPER_LANGUAGE", None)
    flags: list[str] = []

    start = time.monotonic()

    tmp_audio: Optional[str] = None
    try:
        # ── Step 1: Check audio streams ───────────────────────────────────
        _assert_has_audio(file_path)

        # ── Step 2: Extract audio → 16-kHz mono WAV ───────────────────────
        tmp_audio = _extract_audio(file_path)

        # ── Step 3: Transcribe with Whisper ───────────────────────────────
        model = _load_model(effective_model)
        result = _transcribe(model, tmp_audio, language=effective_lang)

    finally:
        if tmp_audio and os.path.exists(tmp_audio):
            try:
                os.remove(tmp_audio)
            except OSError as exc:
                logger.warning("Could not delete temp audio file %s: %s", tmp_audio, exc)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    transcription: str = result.get("text", "").strip()
    if not transcription:
        raise EmptyExtractionError(
            "No speech could be detected in this video.",
            detail="Whisper returned an empty transcription.",
        )

    segments = _format_segments(result.get("segments", []))
    word_count = len(transcription.split())
    duration = result.get("segments", [{}])[-1].get("end", 0.0) if segments else 0.0

    if word_count < 5:
        flags.append("LOW_SPEECH_CONTENT")

    detected_lang = result.get("language", effective_lang or "unknown")

    logger.info(
        "STT complete: %d words, lang=%s, model=%s, %.1fs audio, %d ms",
        word_count, detected_lang, effective_model, duration, elapsed_ms,
    )

    return STTResult(
        transcription=transcription,
        language=detected_lang,
        duration_seconds=round(duration, 2),
        segments=segments,
        word_count=word_count,
        processing_time_ms=elapsed_ms,
        model_size=effective_model,
        flags=flags,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _assert_has_audio(video_path: str) -> None:
    """
    Use ffprobe to check that the video file has at least one audio stream.
    Raises NoAudioTrackError if none are found.
    """
    ffprobe = getattr(settings, "FFPROBE_PATH", "ffprobe")
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "a",
        video_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise AudioExtractionError(
            "ffprobe is not installed or not found in PATH.",
            detail="FileNotFoundError when calling ffprobe.",
        )
    except subprocess.TimeoutExpired:
        raise AudioExtractionError("ffprobe timed out while probing the video.")

    if result.returncode != 0:
        raise InvalidVideoError(
            "Could not read the video file.",
            detail=f"ffprobe error: {result.stderr[:500]}",
        )

    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise InvalidVideoError("ffprobe returned unreadable output.")

    if not probe_data.get("streams"):
        raise NoAudioTrackError(
            "This video has no audio track and cannot be transcribed.",
            detail=f"ffprobe found 0 audio streams in {video_path}",
        )


def _extract_audio(video_path: str) -> str:
    """
    Run ffmpeg to extract audio from the video into a temporary WAV file.

    Output format:
      - Codec  : PCM signed 16-bit little-endian (pcm_s16le)
      - Rate   : 16 000 Hz  (Whisper's native sample rate)
      - Channels: 1 (mono)

    Returns the path of the temp WAV file.
    """
    ffmpeg = getattr(settings, "FFMPEG_PATH", "ffmpeg")

    tmp_dir = tempfile.gettempdir()
    # Use a fixed-extension file so Whisper can find it reliably
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav", dir=tmp_dir)
    os.close(tmp_fd)

    cmd = [
        ffmpeg,
        "-y",                       # Overwrite without asking
        "-i", video_path,
        "-vn",                       # Drop video stream
        "-acodec", "pcm_s16le",      # Uncompressed PCM
        "-ar", "16000",              # 16 kHz
        "-ac", "1",                  # Mono
        tmp_path,
    ]

    logger.debug("Extracting audio: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,   # 10 min ceiling for large files
        )
    except FileNotFoundError:
        raise AudioExtractionError(
            "ffmpeg is not installed or not found in PATH.",
            detail="FileNotFoundError when calling ffmpeg.",
        )
    except subprocess.TimeoutExpired:
        raise AudioExtractionError("ffmpeg timed out during audio extraction.")

    if proc.returncode != 0:
        raise AudioExtractionError(
            "Audio extraction failed.",
            detail=f"ffmpeg stderr: {proc.stderr[:1000]}",
        )

    if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
        raise AudioExtractionError(
            "ffmpeg produced an empty audio file.",
            detail=f"Output file is missing or zero bytes: {tmp_path}",
        )

    logger.debug("Audio extracted to %s (%d bytes)", tmp_path, os.path.getsize(tmp_path))
    return tmp_path


def _load_model(model_size: str):
    """
    Load and cache the Whisper model at the process level.
    Subsequent calls with the same model_size return the cached instance
    without touching disk.
    """
    if model_size not in _MODEL_CACHE:
        try:
            import whisper  # type: ignore[import]
        except ImportError:
            raise WhisperError(
                "Whisper is not installed. Run: pip install openai-whisper",
                detail="ImportError for openai-whisper.",
            )

        logger.info("Loading Whisper model: %s", model_size)
        try:
            _MODEL_CACHE[model_size] = whisper.load_model(model_size)
            logger.info("Whisper model '%s' loaded and cached.", model_size)
        except Exception as exc:
            raise WhisperError(
                f"Failed to load Whisper model '{model_size}'.",
                detail=str(exc),
            )

    return _MODEL_CACHE[model_size]


def _transcribe(model, audio_path: str, language: Optional[str]) -> dict:
    """
    Run Whisper transcription and return the raw result dict.
    Passes `language` only when explicitly provided; otherwise Whisper
    auto-detects the language from the first 30 s of audio.
    """
    kwargs: dict = {
        "verbose": False,
        "fp16": False,  # Use FP32 for CPU compatibility
    }
    if language:
        kwargs["language"] = language

    try:
        result = model.transcribe(audio_path, **kwargs)
    except Exception as exc:
        raise WhisperError(
            "Whisper transcription failed.",
            detail=str(exc),
        )

    return result


def _format_segments(raw_segments: list) -> list[dict]:
    """
    Normalise Whisper segment dicts to a stable schema:
        { id, start, end, text }
    """
    out = []
    for seg in raw_segments:
        out.append({
            "id": seg.get("id", 0),
            "start": round(float(seg.get("start", 0)), 2),
            "end": round(float(seg.get("end", 0)), 2),
            "text": seg.get("text", "").strip(),
        })
    return out
