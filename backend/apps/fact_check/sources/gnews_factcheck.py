"""
GNews fact-check search — runs targeted queries for debunks and fact-check coverage.

Uses the same GNews API key (GNEWS_API_KEY). Complements the general GNews search
with queries tuned for misinformation / fact-check articles.
"""

from __future__ import annotations

import logging

from apps.fact_check.exceptions import FactCheckError
from core.search_query import build_search_query
from .base import ArticleDTO, BaseSource
from .gnews import GNewsSource

logger = logging.getLogger(__name__)


class GNewsFactCheckSource(BaseSource):
    slug = "gnews_factcheck"

    def __init__(self):
        self._gnews = GNewsSource()

    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        if not self._gnews._api_key:
            logger.debug("GNews fact-check skipped: GNEWS_API_KEY is not set.")
            return []

        words = (build_search_query(query) or query).split()[:3]
        base = " ".join(words)
        if not base:
            return []

        merged: list[ArticleDTO] = []
        seen_urls: set[str] = set()

        # Short misinformation-focused queries (free tier returns 0 for long phrases)
        for q in (f"{words[0]} misinformation" if words else base, base):
            if len(merged) >= max_results:
                break
            try:
                batch = self._gnews.search(q, max_results=max_results)
            except FactCheckError as exc:
                logger.warning("GNews fact-check search failed (%r): %s", q, exc.detail)
                continue
            for dto in batch:
                if dto.url and dto.url not in seen_urls:
                    seen_urls.add(dto.url)
                    merged.append(dto)

        logger.info(
            "GNews fact-check returned %d articles for query=%r",
            len(merged),
            base[:60],
        )
        return merged[:max_results]
