"""
DuckDuckGo News connector.

Uses the `duckduckgo-search` library (no API key required).
Returns recent news articles matching the query from a wide range of sources.

Result shape from DDGS().news():
    {
      "date":   "2024-03-15T12:00:00+00:00",
      "title":  "Article title",
      "body":   "Article snippet / description",
      "url":    "https://...",
      "image":  "https://... (optional)",
      "source": "Reuters",
    }
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apps.fact_check.credibility import get_weight, is_trusted
from core.search_query import build_search_query
from .base import ArticleDTO, BaseSource

logger = logging.getLogger(__name__)

# Maximum characters sent to DDG (long queries rarely improve results)
_MAX_QUERY_CHARS = 150


class DuckDuckGoSource(BaseSource):
    """
    News search via DuckDuckGo — zero API key, zero cost.
    Falls back gracefully if the library raises or returns nothing.
    """

    slug = "duckduckgo"

    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("duckduckgo-search is not installed; skipping DDG source.")
            return []

        truncated = (build_search_query(query) or query)[:_MAX_QUERY_CHARS].strip()
        if not truncated:
            return []

        try:
            raw = DDGS().news(keywords=truncated, max_results=max_results)
        except Exception as exc:
            # DDG blocks, rate-limits, or times out occasionally — non-fatal
            logger.warning("DuckDuckGo news search failed: %s", exc)
            return []

        results: list[ArticleDTO] = []
        for item in raw or []:
            try:
                source_name = item.get("source", "").strip()
                dto = ArticleDTO(
                    title=item.get("title", "").strip(),
                    source=source_name,
                    url=item.get("url", ""),
                    published_at=self._normalise_date(item.get("date", "")),
                    description=item.get("body", "").strip(),
                    credibility_weight=get_weight(source_name),
                    is_trusted=is_trusted(source_name),
                )
                if dto.title and dto.url:
                    results.append(dto)
            except Exception as exc:
                logger.warning("Skipping malformed DDG article: %s", exc)

        logger.info("DuckDuckGo returned %d articles for query=%r", len(results), truncated[:60])
        return results

    @staticmethod
    def _normalise_date(raw: str) -> str:
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return raw
