"""
GNews API connector.

Docs  : https://gnews.io/docs/v4
Plan  : Free tier — 100 requests / day, 10 articles / request
Quota : Tracked via Django cache so the limit is respected across workers.

Environment variables (read from Django settings):
    GNEWS_API_KEY        — required
    GNEWS_MAX_RESULTS    — default 5  (max 10 on free tier)
    GNEWS_LANGUAGE       — default "en"
    GNEWS_COUNTRY        — default "" (any)
    SOURCE_REQUEST_TIMEOUT — shared HTTP timeout (seconds)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from django.conf import settings
from core.http import get as http_get
from django.core.cache import cache

from apps.fact_check.credibility import get_weight, is_trusted
from core.search_query import build_search_query
from apps.fact_check.exceptions import (
    FactCheckError,
    InvalidAPIKeyError,
    ParseError,
    RateLimitError,
    SearchTimeoutError,
    SourceUnavailableError,
)
from .base import ArticleDTO, BaseSource

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

_BASE_URL = "https://gnews.io/api/v4/search"
_DAILY_LIMIT = 100               # Free tier hard cap
_CACHE_KEY = "gnews:daily_calls"
_CACHE_TTL = 86_400              # 24 hours in seconds
_MAX_QUERY_CHARS = 200           # GNews truncates longer queries silently


class GNewsSource(BaseSource):
    """
    Fetches the top-N news articles from GNews related to a query string.

    Rate-limit handling
    ───────────────────
    - A Django-cache counter tracks daily API calls.
    - If the counter hits _DAILY_LIMIT, RateLimitError is raised **before**
      making any HTTP request (saves quota on misconfigured deployments).
    - When GNews itself returns HTTP 429, the counter is reset to _DAILY_LIMIT
      so subsequent calls short-circuit immediately.
    """

    slug = "gnews"

    def __init__(self):
        self._api_key: str = getattr(settings, "GNEWS_API_KEY", "")
        self._max_results: int = getattr(settings, "GNEWS_MAX_RESULTS", 5)
        self._language: str = getattr(settings, "GNEWS_LANGUAGE", "en")
        self._country: str = getattr(settings, "GNEWS_COUNTRY", "")
        self._timeout: int = getattr(settings, "SOURCE_REQUEST_TIMEOUT", 10)

    # ── Public API ──────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 0) -> list[ArticleDTO]:
        """
        Search GNews with fact-check oriented queries first, then a general query.
        """
        if not self._api_key:
            logger.debug("GNews skipped: API key is not configured.")
            return []

        n = max_results or self._max_results
        words = (build_search_query(query) or query).split()[:3]
        base = " ".join(words)
        if not base:
            return []

        seen_urls: set[str] = set()
        merged: list[ArticleDTO] = []

        search_queries = []
        if words:
            search_queries.append(f"{words[0]} misinformation")
        search_queries.append(base)

        for q in search_queries:
            if len(merged) >= n:
                break
            try:
                batch = self._search_single(q, n)
            except FactCheckError:
                continue
            for dto in batch:
                if dto.url and dto.url not in seen_urls:
                    seen_urls.add(dto.url)
                    merged.append(dto)

        logger.info("GNews returned %d articles for query=%r", len(merged), base[:60])
        return merged[:n]

    def _search_single(self, query: str, max_results: int) -> list[ArticleDTO]:
        """One GNews API request."""
        from apps.fact_check.exceptions import FactCheckError

        self._check_rate_limit()
        params = self._build_params(query, max_results)
        logger.debug("GNews search: query=%r max=%d", query[:60], max_results)
        raw = self._http_get(params)
        self._increment_counter()
        return self._parse(raw)

    # ── Private helpers ─────────────────────────────────────────────────────

    def _build_params(self, query: str, max_results: int) -> dict:
        # Short queries work best on GNews free tier (long queries return 0 articles)
        keywords = (build_search_query(query) or query).split()
        truncated = " ".join(keywords[:5])[:_MAX_QUERY_CHARS].strip()
        params: dict = {
            "q": truncated,
            "max": min(max_results, 10),   # Free tier ceiling is 10
            "apikey": self._api_key,
            "lang": self._language,
            # Free tier: sortby=relevance often returns zero articles (paid-only)
            "sortby": "publishedAt",
        }
        if self._country:
            params["country"] = self._country
        return params

    def _http_get(self, params: dict) -> dict:
        try:
            resp = http_get(_BASE_URL, params=params, timeout=self._timeout)
        except requests.Timeout:
            raise SearchTimeoutError(
                "GNews request timed out. Please try again.",
                detail=f"Timeout after {self._timeout}s.",
            )
        except ConnectionError as exc:
            raise SourceUnavailableError(
                "Could not reach GNews. Check your internet connection.",
                detail=str(exc),
            )

        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError as exc:
                raise ParseError(
                    "GNews returned an unparseable response.",
                    detail=str(exc),
                )

        if resp.status_code == 401 or resp.status_code == 403:
            raise InvalidAPIKeyError(
                "News service is temporarily unavailable.",
                detail=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 0))
            raise RateLimitError(source="GNews", retry_after=retry_after)

        raise SourceUnavailableError(
            f"GNews returned an unexpected error (HTTP {resp.status_code}).",
            detail=resp.text[:300],
        )

    def _parse(self, data: dict) -> list[ArticleDTO]:
        raw_articles = data.get("articles")
        if not isinstance(raw_articles, list):
            raise ParseError(
                "GNews response did not contain an articles list.",
                detail=f"Keys present: {list(data.keys())}",
            )

        results: list[ArticleDTO] = []
        for item in raw_articles:
            try:
                source_name = (
                    item.get("source", {}).get("name", "")
                    if isinstance(item.get("source"), dict)
                    else str(item.get("source", ""))
                )
                dto = ArticleDTO(
                    title=item.get("title", "").strip(),
                    source=source_name,
                    url=item.get("url", ""),
                    published_at=self._normalise_date(item.get("publishedAt", "")),
                    description=(item.get("description") or "").strip(),
                    credibility_weight=get_weight(source_name),
                    is_trusted=is_trusted(source_name),
                )
                results.append(dto)
            except Exception as exc:
                logger.warning("Skipping malformed GNews article: %s", exc)
                continue

        return results

    # ── Rate-limit helpers ───────────────────────────────────────────────────

    def _check_rate_limit(self) -> None:
        count = cache.get(_CACHE_KEY, 0)
        if count >= _DAILY_LIMIT:
            raise RateLimitError(
                source="GNews",
                retry_after=0,
            )

    def _increment_counter(self) -> None:
        try:
            cache.add(_CACHE_KEY, 0, _CACHE_TTL)
            cache.incr(_CACHE_KEY)
        except Exception as exc:
            # Cache backend unavailable — log but don't block the request
            logger.warning("Could not increment GNews rate-limit counter: %s", exc)

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise_date(raw: str) -> str:
        """
        Normalise GNews date strings to ISO 8601 UTC.
        GNews returns dates like "2024-03-15T12:00:00Z" — already valid, but
        we re-parse and re-format to guarantee consistency.
        """
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return raw
