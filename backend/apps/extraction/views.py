"""
Direct extraction API views.

These endpoints run synchronously and are designed for:
  - Testing the OCR / STT pipeline independently
  - Client-side "extract only" workflows where the caller handles
    the fact-checking themselves

Endpoints
─────────
  POST /api/extract/image/  →  ImageExtractView
  POST /api/extract/video/  →  VideoExtractView
"""

import logging
import tempfile
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from .serializers import ImageExtractSerializer, VideoExtractSerializer
from .ocr import extract_text_from_bytes
from .speech import extract_text_from_video
from .exceptions import (
    ExtractionError,
    EmptyExtractionError,
    InvalidImageError,
    InvalidVideoError,
    OCREngineError,
    NoAudioTrackError,
    AudioExtractionError,
    WhisperError,
)

logger = logging.getLogger(__name__)


class ImageExtractView(APIView):
    """
    POST /api/extract/image/

    Accept an image file, run Tesseract OCR, and return the extracted text.

    Request (multipart/form-data):
        file        — required, image file
        lang        — optional, Tesseract language code (default: "eng")
        preprocess  — optional, bool (default: true)

    Response 200:
        {
          "extracted_text":    string,
          "word_count":        int,
          "char_count":        int,
          "is_empty":          bool,
          "processing_time_ms": int,
          "flags":             string[]
        }
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ImageExtractSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        lang = serializer.validated_data.get("lang", "")
        preprocess = serializer.validated_data.get("preprocess", True)

        # Read file bytes once so we don't depend on file.path (works for
        # both on-disk and in-memory uploaded files)
        image_bytes = file.read()

        try:
            result = extract_text_from_bytes(
                image_bytes,
                lang=lang,
                preprocess_image=preprocess,
            )
        except InvalidImageError as exc:
            logger.warning("Invalid image upload: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except OCREngineError as exc:
            logger.error("Tesseract engine error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmptyExtractionError as exc:
            logger.info("OCR returned empty text: %s", exc.detail)
            return Response(
                {
                    "extracted_text": "",
                    "word_count": 0,
                    "char_count": 0,
                    "is_empty": True,
                    "processing_time_ms": 0,
                    "flags": ["NO_TEXT_DETECTED"],
                    "message": exc.user_message,
                },
                status=status.HTTP_200_OK,
            )
        except ExtractionError as exc:
            logger.error("OCR extraction error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "extracted_text": result.text,
                "word_count": result.word_count,
                "char_count": result.char_count,
                "is_empty": result.is_empty,
                "processing_time_ms": result.processing_time_ms,
                "flags": result.flags,
            },
            status=status.HTTP_200_OK,
        )


class VideoExtractView(APIView):
    """
    POST /api/extract/video/

    Accept a video file, extract audio with ffmpeg, transcribe with Whisper,
    and return the transcription.

    Request (multipart/form-data):
        file        — required, video file
        language    — optional, ISO-639-1 hint (e.g. "en"); blank = auto-detect
        model_size  — optional, one of: tiny / base / small / medium / large

    Response 200:
        {
          "transcription":      string,
          "language":           string,
          "duration_seconds":   float,
          "word_count":         int,
          "segments":           [{ id, start, end, text }],
          "processing_time_ms": int,
          "model_size":         string,
          "flags":              string[]
        }
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VideoExtractSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = serializer.validated_data["file"]
        language = serializer.validated_data.get("language") or None
        model_size = serializer.validated_data.get("model_size", "")

        # Write the uploaded file to a temp path so ffmpeg can read it.
        # We must preserve the original extension for ffmpeg to detect the
        # container format correctly.
        original_name = getattr(file, "name", "upload.mp4")
        suffix = os.path.splitext(original_name)[-1] or ".mp4"

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(tmp_fd, "wb") as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)

            result = extract_text_from_video(
                tmp_path,
                language=language,
                model_size=model_size,
            )
        except (InvalidVideoError, NoAudioTrackError) as exc:
            logger.warning("Invalid video: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except AudioExtractionError as exc:
            logger.error("ffmpeg error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except WhisperError as exc:
            logger.error("Whisper error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except EmptyExtractionError as exc:
            logger.info("STT returned empty text: %s", exc.detail)
            return Response(
                {
                    "transcription": "",
                    "language": "unknown",
                    "duration_seconds": 0.0,
                    "word_count": 0,
                    "segments": [],
                    "processing_time_ms": 0,
                    "model_size": model_size or "n/a",
                    "flags": ["NO_SPEECH_DETECTED"],
                    "message": exc.user_message,
                },
                status=status.HTTP_200_OK,
            )
        except ExtractionError as exc:
            logger.error("STT extraction error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        return Response(
            {
                "transcription": result.transcription,
                "language": result.language,
                "duration_seconds": result.duration_seconds,
                "word_count": result.word_count,
                "segments": result.segments,
                "processing_time_ms": result.processing_time_ms,
                "model_size": result.model_size,
                "flags": result.flags,
            },
            status=status.HTTP_200_OK,
        )
