import logging
import threading
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny

from .models import Upload, VerificationResult
from .serializers import (
    UploadCreateSerializer,
    UploadDetailSerializer,
    VerifyRequestSerializer,
    VerificationResultSerializer,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/upload/
# ──────────────────────────────────────────────────────────────────────────────

class UploadView(APIView):
    """
    Accept a file (image/video) or plain text and persist it as an Upload.
    Returns the Upload record with status=pending — verification is not
    triggered here; call POST /api/verify/ next.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [AllowAny]   # tighten to IsAuthenticated in production

    def post(self, request):
        serializer = UploadCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = serializer.save()
        logger.info("Upload created: id=%s type=%s", upload.id, upload.file_type)

        return Response(
            {
                "message": "Upload successful. Call POST /api/verify/ to start analysis.",
                "upload": UploadDetailSerializer(upload).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/verify/
# ──────────────────────────────────────────────────────────────────────────────

class VerifyView(APIView):
    """
    Trigger the asynchronous fact-checking pipeline for an existing Upload.

    Flow:
      1. Validate upload_id
      2. Mark Upload as PROCESSING
      3. Dispatch Celery task
      4. Return task ID so the client can poll for results
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRequestSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload: Upload = serializer.context["upload"]

        from tasks.verification_tasks import execute_pipeline

        task_id = f"thread-{uuid.uuid4()}"
        upload.status = Upload.Status.PROCESSING
        upload.celery_task_id = task_id
        upload.save(update_fields=["status", "celery_task_id", "updated_at"])

        # Run pipeline in a background thread (no Redis/Celery worker required)
        thread = threading.Thread(
            target=execute_pipeline,
            args=(str(upload.id),),
            daemon=True,
        )
        thread.start()

        logger.info(
            "Verification dispatched (thread): upload=%s task=%s", upload.id, task_id
        )

        return Response(
            {
                "message": "Verification started.",
                "upload_id": str(upload.id),
                "task_id": task_id,
                "status_url": f"/api/upload/{upload.id}/",
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/result/<id>/
# ──────────────────────────────────────────────────────────────────────────────

class ResultView(APIView):
    """
    Return the VerificationResult for a given result UUID.
    Also accepts the Upload UUID — responds with current processing
    status when the result is not yet available.
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        # Support lookup by both result ID and upload ID
        result = (
            VerificationResult.objects.select_related("upload")
            .filter(pk=pk)
            .first()
        )

        if result is None:
            # Try treating pk as an upload UUID
            upload = Upload.objects.filter(pk=pk).first()
            if upload is None:
                return Response(
                    {"error": "No result or upload found with this ID."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if upload.status in (Upload.Status.PENDING, Upload.Status.PROCESSING):
                return Response(
                    {
                        "upload_id": str(upload.id),
                        "status": upload.status,
                        "message": "Analysis is still in progress. Please try again shortly.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            if upload.status == Upload.Status.FAILED:
                return Response(
                    {
                        "upload_id": str(upload.id),
                        "status": upload.status,
                        "message": "Verification failed. Please re-submit the upload.",
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            return Response(
                {"error": "Result not found for this upload."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VerificationResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/upload/<id>/   (status polling endpoint)
# ──────────────────────────────────────────────────────────────────────────────

class UploadDetailView(APIView):
    """
    Return full Upload details including the embedded result when ready.
    Useful for client-side polling.
    """

    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            upload = Upload.objects.select_related("result").get(pk=pk)
        except Upload.DoesNotExist:
            return Response(
                {"error": "Upload not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UploadDetailSerializer(upload)
        return Response(serializer.data, status=status.HTTP_200_OK)
