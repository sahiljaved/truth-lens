"""
Base settings shared across all environments.
"""

from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_results",
    # Local apps
    "apps.verifier",
    "apps.extraction",
    "apps.fact_check",
    "apps.scoring",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="truthlens_db"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = config("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / config("MEDIA_ROOT", default="media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────
# Django REST Framework
# ──────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# ──────────────────────────────────────────────
# SimpleJWT
# ──────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ──────────────────────────────────────────────
# Celery
# ──────────────────────────────────────────────
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# ──────────────────────────────────────────────
# Upload constraints
# ──────────────────────────────────────────────
MAX_IMAGE_SIZE = config("MAX_IMAGE_SIZE", default=10 * 1024 * 1024, cast=int)   # 10 MB
MAX_VIDEO_SIZE = config("MAX_VIDEO_SIZE", default=100 * 1024 * 1024, cast=int)  # 100 MB
MAX_TEXT_LENGTH = config("MAX_TEXT_LENGTH", default=50_000, cast=int)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}

# ──────────────────────────────────────────────
# OCR (Tesseract)
# ──────────────────────────────────────────────
# Full path to the Tesseract binary.
# Windows example: C:/Program Files/Tesseract-OCR/tesseract.exe
# Leave blank to rely on system PATH.
TESSERACT_CMD = config("TESSERACT_CMD", default="")
TESSERACT_LANG = config("TESSERACT_LANG", default="eng")

# ──────────────────────────────────────────────
# Speech-to-Text (Whisper + ffmpeg)
# ──────────────────────────────────────────────
# Whisper model size: tiny | base | small | medium | large
# "small" is a good balance of speed and accuracy for most use-cases.
ENABLE_VIDEO_STT = config("ENABLE_VIDEO_STT", default=True, cast=bool)
WHISPER_MODEL_SIZE = config("WHISPER_MODEL_SIZE", default="small")
# Force a specific language; None = Whisper auto-detects from audio.
WHISPER_LANGUAGE = config("WHISPER_LANGUAGE", default="")  # blank = auto

# Full paths to ffmpeg/ffprobe binaries.
# Leave blank to rely on system PATH (recommended for Linux/macOS).
FFMPEG_PATH = config("FFMPEG_PATH", default="ffmpeg")
FFPROBE_PATH = config("FFPROBE_PATH", default="ffprobe")

# ──────────────────────────────────────────────
# Fact-check source settings
# ──────────────────────────────────────────────
SOURCE_REQUEST_TIMEOUT = config("SOURCE_REQUEST_TIMEOUT", default=10, cast=int)
# Set False on Windows if Python raises SSL CERTIFICATE_VERIFY_FAILED
HTTP_SSL_VERIFY = config("HTTP_SSL_VERIFY", default=True, cast=bool)
GOOGLE_FACTCHECK_API_KEY = config("GOOGLE_FACTCHECK_API_KEY", default="")

# ── GNews ──────────────────────────────────────
# Free tier: 100 requests/day, 10 articles/request
# Sign up: https://gnews.io/
GNEWS_API_KEY = config("GNEWS_API_KEY", default="")
GNEWS_MAX_RESULTS = config("GNEWS_MAX_RESULTS", default=5, cast=int)
GNEWS_LANGUAGE = config("GNEWS_LANGUAGE", default="en")
GNEWS_COUNTRY = config("GNEWS_COUNTRY", default="")  # blank = worldwide
