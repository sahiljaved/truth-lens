from rest_framework import serializers
from django.conf import settings


# ──────────────────────────────────────────────────────────────────────────────
# Input serializers
# ──────────────────────────────────────────────────────────────────────────────

class ImageExtractSerializer(serializers.Serializer):
    """Validates an image upload for the direct OCR endpoint."""

    file = serializers.ImageField(
        help_text="Image file to extract text from (JPEG, PNG, WEBP, GIF)."
    )
    lang = serializers.CharField(
        required=False,
        default="",
        max_length=20,
        help_text=(
            "Tesseract language code(s), e.g. 'eng', 'eng+fra'. "
            "Leave blank to use the server default."
        ),
    )
    preprocess = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Apply image preprocessing (contrast, sharpening, binarisation).",
    )

    def validate_file(self, file):
        content_type = getattr(file, "content_type", "")
        allowed = getattr(settings, "ALLOWED_IMAGE_TYPES", set())
        if allowed and content_type not in allowed:
            raise serializers.ValidationError(
                f"Unsupported image type '{content_type}'. "
                f"Accepted: {', '.join(sorted(allowed))}."
            )
        max_size = getattr(settings, "MAX_IMAGE_SIZE", 10 * 1024 * 1024)
        if file.size > max_size:
            mb = max_size // (1024 * 1024)
            raise serializers.ValidationError(f"Image exceeds the {mb} MB limit.")
        return file


class VideoExtractSerializer(serializers.Serializer):
    """Validates a video upload for the direct STT endpoint."""

    WHISPER_MODEL_CHOICES = ["tiny", "base", "small", "medium", "large"]

    file = serializers.FileField(
        help_text="Video file to transcribe (MP4, WEBM, MOV)."
    )
    language = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=10,
        help_text=(
            "ISO-639-1 language hint, e.g. 'en', 'fr'. "
            "Leave blank for automatic detection."
        ),
    )
    model_size = serializers.ChoiceField(
        choices=WHISPER_MODEL_CHOICES,
        required=False,
        default="",
        help_text=(
            "Whisper model size. Larger = more accurate but slower. "
            "Leave blank to use the server default."
        ),
    )

    def validate_file(self, file):
        content_type = getattr(file, "content_type", "")
        allowed = getattr(settings, "ALLOWED_VIDEO_TYPES", set())
        if allowed and content_type not in allowed:
            raise serializers.ValidationError(
                f"Unsupported video type '{content_type}'. "
                f"Accepted: {', '.join(sorted(allowed))}."
            )
        max_size = getattr(settings, "MAX_VIDEO_SIZE", 100 * 1024 * 1024)
        if file.size > max_size:
            mb = max_size // (1024 * 1024)
            raise serializers.ValidationError(f"Video exceeds the {mb} MB limit.")
        return file

    def validate_language(self, value):
        return value.strip().lower() or None


# ──────────────────────────────────────────────────────────────────────────────
# Output serializers (read-only, for documentation / schema generation)
# ──────────────────────────────────────────────────────────────────────────────

class OCRResponseSerializer(serializers.Serializer):
    extracted_text = serializers.CharField()
    word_count = serializers.IntegerField()
    char_count = serializers.IntegerField()
    is_empty = serializers.BooleanField()
    processing_time_ms = serializers.IntegerField()
    flags = serializers.ListField(child=serializers.CharField())


class SegmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    start = serializers.FloatField()
    end = serializers.FloatField()
    text = serializers.CharField()


class STTResponseSerializer(serializers.Serializer):
    transcription = serializers.CharField()
    language = serializers.CharField()
    duration_seconds = serializers.FloatField()
    word_count = serializers.IntegerField()
    segments = SegmentSerializer(many=True)
    processing_time_ms = serializers.IntegerField()
    model_size = serializers.CharField()
    flags = serializers.ListField(child=serializers.CharField())
