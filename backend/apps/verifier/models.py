import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


def upload_to(instance, filename):
    """Route uploaded files into typed subdirectories."""
    return f"uploads/{instance.file_type}/{instance.id}/{filename}"


class Upload(models.Model):
    """
    Stores every submitted piece of content — image, video, or plain text.
    Text submissions store their content in `raw_text`; file submissions
    store the file in `file`.
    """

    class FileType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        TEXT = "text", "Text"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploads",
    )
    file = models.FileField(upload_to=upload_to, null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    raw_text = models.TextField(blank=True, default="")
    extracted_text = models.TextField(blank=True, default="")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["file_type"]),
            models.Index(fields=["user", "-uploaded_at"]),
        ]

    def __str__(self):
        return f"Upload({self.file_type}, {self.status}) — {self.id}"


class VerificationResult(models.Model):
    """
    Stores the structured output of the fact-checking pipeline for a given
    Upload. One-to-one relationship: each upload has at most one result.
    """

    class Verdict(models.TextChoices):
        LIKELY_TRUE = "LIKELY_TRUE", "Likely True"
        UNCERTAIN = "UNCERTAIN", "Uncertain"
        LIKELY_FALSE = "LIKELY_FALSE", "Likely False"
        UNVERIFIABLE = "UNVERIFIABLE", "Unverifiable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    upload = models.OneToOneField(
        Upload, on_delete=models.CASCADE, related_name="result"
    )
    confidence_score = models.FloatField(
        help_text="Normalised score between 0.0 and 1.0"
    )
    verdict = models.CharField(
        max_length=20, choices=Verdict.choices, default=Verdict.UNVERIFIABLE
    )
    summary = models.TextField()
    # Structured JSON fields — stored as Python lists/dicts
    sources = models.JSONField(default=list, blank=True)
    flags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Result(score={self.confidence_score:.2f}, verdict={self.verdict})"
            f" — upload={self.upload_id}"
        )

    # ------------------------------------------------------------------ #
    # Derived helpers                                                      #
    # ------------------------------------------------------------------ #

    @property
    def score_percent(self) -> int:
        """Return score as an integer percentage (0–100)."""
        return round(self.confidence_score * 100)

    @property
    def critical_flags(self) -> list:
        return [f for f in self.flags if f.get("severity") == "CRITICAL"]
