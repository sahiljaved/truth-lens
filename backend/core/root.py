from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class RootView(APIView):
    """Friendly response when someone opens the API base URL in a browser."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "service": "TruthLens API",
                "status": "running",
                "message": "This is the backend API. Open the frontend URL to use the app.",
                "health": request.build_absolute_uri("/api/health/"),
                "docs": {
                    "upload": "POST /api/upload/",
                    "verify": "POST /api/verify/",
                    "poll": "GET /api/upload/{id}/",
                },
            }
        )
