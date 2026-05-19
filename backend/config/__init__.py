from core.http import configure_ssl

configure_ssl()

from .celery import app as celery_app

__all__ = ("celery_app",)