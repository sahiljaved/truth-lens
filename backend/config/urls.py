from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
from core.health import HealthView

urlpatterns = [
    path("api/health/", HealthView.as_view(), name="health"),
    path("admin/", admin.site.urls),

    # Auth
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),

    # Verifier app
    path("api/", include("apps.verifier.urls")),

    # Extraction (direct OCR / STT endpoints)
    path("api/", include("apps.extraction.urls")),

    # Fact-check (news search + standalone verify)
    path("api/", include("apps.fact_check.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
