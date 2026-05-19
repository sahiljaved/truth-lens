import logging

from django.conf import settings
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

from core.security import public_error_payload

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to produce a consistent error
    envelope. Never exposes stack traces, settings names, or secrets.
    """
    response = exception_handler(exc, context)

    if response is not None:
        payload = public_error_payload(
            _extract_message(response.data),
            status_code=response.status_code,
            detail=response.data if settings.DEBUG else None,
        )
        response.data = payload
        return response

    # Unhandled server-side exceptions — log full detail, return generic message
    logger.exception("Unhandled exception in view %s", context.get("view"))
    return Response(
        public_error_payload(
            "An unexpected server error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_message(data) -> str:
    """Pull a flat string from whatever DRF puts in response.data."""
    if isinstance(data, dict):
        for key in ("detail", "non_field_errors", "message", "error"):
            if key in data:
                return _extract_message(data[key])
        first = next(iter(data.values()), None)
        return _extract_message(first) if first else "Unknown error."
    if isinstance(data, list):
        return _extract_message(data[0]) if data else "Unknown error."
    return str(data)
