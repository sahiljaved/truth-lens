from rest_framework import serializers
from django.conf import settings

from .models import Upload, VerificationResult


# ──────────────────────────────────────────────────────────────────────────────
# Source & Flag nested serializers (read-only, no DB model needed)
# ──────────────────────────────────────────────────────────────────────────────

class SourceSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.URLField(allow_blank=True)
    published_at = serializers.CharField(allow_blank=True, default="")
    snippet = serializers.CharField(allow_blank=True, default="")
    credibility_weight = serializers.FloatField()
    is_trusted = serializers.BooleanField(default=False)
    similarity_score = serializers.FloatField(default=0.0)
    article_score = serializers.FloatField(default=0.0)


class FlagSerializer(serializers.Serializer):
    type = serializers.CharField()
    severity = serializers.ChoiceField(
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    )
    detail = serializers.CharField(allow_blank=True)


# ──────────────────────────────────────────────────────────────────────────────
# VerificationResult
# ──────────────────────────────────────────────────────────────────────────────

class VerificationResultSerializer(serializers.ModelSerializer):
    score_percent = serializers.ReadOnlyField()
    sources = SourceSerializer(many=True, read_only=True)
    flags = FlagSerializer(many=True, read_only=True)

    class Meta:
        model = VerificationResult
        fields = [
            "id",
            "upload",
            "confidence_score",
            "score_percent",
            "verdict",
            "summary",
            "sources",
            "flags",
            "created_at",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Upload — input serializer (POST /upload)
# ──────────────────────────────────────────────────────────────────────────────

class UploadCreateSerializer(serializers.ModelSerializer):
    """
    Validates and creates an Upload record.
    Accepts either a `file` (image/video) or `raw_text` (text submission).
    Exactly one of the two must be provided.
    """

    file = serializers.FileField(required=False, allow_null=True)
    raw_text = serializers.CharField(
        required=False, allow_blank=False, max_length=settings.MAX_TEXT_LENGTH
    )

    class Meta:
        model = Upload
        fields = ["file", "file_type", "raw_text"]

    # ------------------------------------------------------------------ #
    # Field-level validation                                               #
    # ------------------------------------------------------------------ #

    def validate_file_type(self, value):
        allowed = {choice[0] for choice in Upload.FileType.choices}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid file_type. Must be one of: {', '.join(allowed)}."
            )
        return value

    def validate_file(self, file):
        if file is None:
            return file

        content_type = getattr(file, "content_type", "")

        # Reject files without a detectable MIME type
        if not content_type:
            raise serializers.ValidationError("Cannot determine file MIME type.")

        return file

    # ------------------------------------------------------------------ #
    # Object-level validation                                              #
    # ------------------------------------------------------------------ #

    def validate(self, attrs):
        file = attrs.get("file")
        raw_text = attrs.get("raw_text", "").strip()
        file_type = attrs.get("file_type")

        # Exactly one payload must be provided
        if not file and not raw_text:
            raise serializers.ValidationError(
                "Provide either a `file` or `raw_text`."
            )
        if file and raw_text:
            raise serializers.ValidationError(
                "Provide either a `file` or `raw_text`, not both."
            )

        # Cross-validate file_type against what was submitted
        if file:
            content_type = getattr(file, "content_type", "")
            if file_type == Upload.FileType.IMAGE:
                if content_type not in settings.ALLOWED_IMAGE_TYPES:
                    raise serializers.ValidationError(
                        f"For type 'image', accepted MIME types are: "
                        f"{', '.join(settings.ALLOWED_IMAGE_TYPES)}. "
                        f"Got: {content_type}."
                    )
                if file.size > settings.MAX_IMAGE_SIZE:
                    mb = settings.MAX_IMAGE_SIZE // (1024 * 1024)
                    raise serializers.ValidationError(
                        f"Image exceeds the {mb} MB size limit."
                    )

            elif file_type == Upload.FileType.VIDEO:
                if content_type not in settings.ALLOWED_VIDEO_TYPES:
                    raise serializers.ValidationError(
                        f"For type 'video', accepted MIME types are: "
                        f"{', '.join(settings.ALLOWED_VIDEO_TYPES)}. "
                        f"Got: {content_type}."
                    )
                if file.size > settings.MAX_VIDEO_SIZE:
                    mb = settings.MAX_VIDEO_SIZE // (1024 * 1024)
                    raise serializers.ValidationError(
                        f"Video exceeds the {mb} MB size limit."
                    )

            elif file_type == Upload.FileType.TEXT:
                raise serializers.ValidationError(
                    "For file_type 'text', use the `raw_text` field instead of `file`."
                )

        if raw_text and file_type != Upload.FileType.TEXT:
            raise serializers.ValidationError(
                "When submitting `raw_text`, set file_type to 'text'."
            )

        return attrs

    def create(self, validated_data):
        file = validated_data.get("file")
        instance = Upload(
            file_type=validated_data["file_type"],
            raw_text=validated_data.get("raw_text", ""),
            user=self.context["request"].user
            if self.context["request"].user.is_authenticated
            else None,
        )
        if file:
            instance.original_filename = file.name
            instance.file_size = file.size
            instance.mime_type = getattr(file, "content_type", "")
            instance.file = file

        instance.save()
        return instance


# ──────────────────────────────────────────────────────────────────────────────
# Upload — output serializer (read)
# ──────────────────────────────────────────────────────────────────────────────

class UploadDetailSerializer(serializers.ModelSerializer):
    result = VerificationResultSerializer(read_only=True)

    class Meta:
        model = Upload
        fields = [
            "id",
            "file_type",
            "original_filename",
            "file_size",
            "mime_type",
            "status",
            "extracted_text",
            "uploaded_at",
            "updated_at",
            "result",
        ]
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Verify request serializer (POST /verify)
# ──────────────────────────────────────────────────────────────────────────────

class VerifyRequestSerializer(serializers.Serializer):
    """
    Accepts an upload_id and triggers the fact-checking pipeline.
    """

    upload_id = serializers.UUIDField()

    def validate_upload_id(self, value):
        try:
            upload = Upload.objects.get(pk=value)
        except Upload.DoesNotExist:
            raise serializers.ValidationError("Upload not found.")

        if upload.status == Upload.Status.PROCESSING:
            raise serializers.ValidationError(
                "This upload is already being processed."
            )

        if upload.status == Upload.Status.COMPLETED:
            raise serializers.ValidationError(
                "This upload has already been verified. "
                "Fetch the result via GET /api/result/{id}/."
            )

        self.context["upload"] = upload
        return value
