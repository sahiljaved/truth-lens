"""
Shared HTTP helpers — fixes SSL certificate issues on some Windows Python installs.
"""

from __future__ import annotations

import os
import warnings

import certifi
import requests


def configure_ssl() -> None:
    """Point Python/requests/httpx at certifi's CA bundle."""
    bundle = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", bundle)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
    os.environ.setdefault("CURL_CA_BUNDLE", bundle)


def ssl_verify():
    """
    Return verify= value for requests.
    Set HTTP_SSL_VERIFY=False in .env when Windows Python cannot validate certs.
    """
    try:
        from django.conf import settings
        if not getattr(settings, "HTTP_SSL_VERIFY", True):
            return False
    except Exception:
        pass
    return certifi.where()


def get(url: str, **kwargs) -> requests.Response:
    """GET with SSL settings and a sensible default timeout."""
    kwargs.setdefault("timeout", kwargs.pop("timeout", 10))
    kwargs.setdefault("verify", ssl_verify())
    if kwargs["verify"] is False:
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    return requests.get(url, **kwargs)
