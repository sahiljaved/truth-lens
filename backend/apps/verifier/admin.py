from django.contrib import admin
from .models import Upload, VerificationResult


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = ["id", "file_type", "status", "original_filename", "uploaded_at"]
    list_filter = ["file_type", "status"]
    search_fields = ["id", "original_filename", "extracted_text"]
    readonly_fields = ["id", "uploaded_at", "updated_at", "celery_task_id"]
    ordering = ["-uploaded_at"]


@admin.register(VerificationResult)
class VerificationResultAdmin(admin.ModelAdmin):
    list_display = ["id", "upload", "confidence_score", "verdict", "created_at"]
    list_filter = ["verdict"]
    search_fields = ["id", "summary"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]
