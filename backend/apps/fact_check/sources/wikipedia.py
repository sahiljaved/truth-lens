"""
Wikipedia search connector.

Uses the public MediaWiki API (no API key, no rate-limit beyond polite use).
Useful for verifying factual claims against encyclopaedic content.

API endpoint:
  https://en.wikipedia.org/w/api.php
  action=query, list=search, srsearch={query}, format=json
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import requests
from django.conf import settings
from core.http import get as http_get
from core.search_query import build_search_query

from apps.fact_check.credibility import get_weight, is_trusted
from apps.fact_check.exceptions import SearchTimeoutError, SourceUnavailableError
from .base import ArticleDTO, BaseSource

logger = logging.getLogger(__name__)

_API_URL = "https://en.wikipedia.org/w/api.php"
_WIKI_BASE = "https://en.wikipedia.org/wiki/"
_MAX_QUERY_CHARS = 200
_SOURCE_NAME = "Wikipedia"


class WikipediaSource(BaseSource):
    """
    Searches Wikipedia and returns matching article summaries.
    No API key required; respects Wikipedia's user-agent guidelines.
    """

    slug = "wikipedia"

    def __init__(self):
        self._timeout: int = getattr(settings, "SOURCE_REQUEST_TIMEOUT", 10)

    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        truncated = build_search_query(query) or query[:_MAX_QUERY_CHARS].strip()
        if not truncated:
            return []

        params = {
            "action": "query",
            "list": "search",
            "srsearch": truncated,
            "format": "json",
            "srlimit": min(max_results, 10),
            "srprop": "snippet|wordcount|timestamp",
            "utf8": 1,
        }

        headers = {
            "User-Agent": "TruthLens/1.0 (fact-check research; contact@truthlens.app)"
        }

        try:
            resp = http_get(
                _API_URL,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.Timeout:
            raise SearchTimeoutError(
                "Wikipedia search timed out.",
                detail=f"Timeout after {self._timeout}s.",
            )
        except Exception as exc:
            raise SourceUnavailableError(
                "Could not reach Wikipedia.",
                detail=str(exc),
            )

        raw_results = data.get("query", {}).get("search", [])
        articles: list[ArticleDTO] = []

        for item in raw_results:
            try:
                title = item.get("title", "").strip()
                snippet = self._clean_snippet(item.get("snippet", ""))
                timestamp = item.get("timestamp", "")
                url = _WIKI_BASE + quote(title.replace(" ", "_"), safe="/:@!$&'()*+,;=")

                dto = ArticleDTO(
                    title=title,
                    source=_SOURCE_NAME,
                    url=url,
                    published_at=timestamp,
                    description=snippet,
                    credibility_weight=get_weight(_SOURCE_NAME),
                    is_trusted=is_trusted(_SOURCE_NAME),
                )
                if dto.title:
                    articles.append(dto)
            except Exception as exc:
                logger.warning("Skipping malformed Wikipedia result: %s", exc)

        logger.info("Wikipedia returned %d results for query=%r", len(articles), truncated[:60])
        return articles

    @staticmethod
    def _clean_snippet(snippet: str) -> str:
        """Strip MediaWiki HTML highlight tags from snippet text."""
        return (
            snippet
            .replace('<span class="searchmatch">', "")
            .replace("</span>", "")
            .strip()
        )
