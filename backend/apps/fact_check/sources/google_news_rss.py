"""
Google News RSS fallback — no API key, works when DuckDuckGo is blocked.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

from django.conf import settings

from apps.fact_check.credibility import get_weight, is_trusted
from core.http import get
from core.search_query import build_search_query
from .base import ArticleDTO, BaseSource

logger = logging.getLogger(__name__)

_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class GoogleNewsRSSSource(BaseSource):
    slug = "google_news_rss"

    def __init__(self):
        self._timeout = getattr(settings, "SOURCE_REQUEST_TIMEOUT", 15)

    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        search_q = build_search_query(query) or query[:150].strip()
        if not search_q:
            return []

        url = _RSS_URL.format(query=quote_plus(search_q))
        try:
            resp = get(url, timeout=self._timeout, headers={"User-Agent": "TruthLens/1.0"})
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Google News RSS failed: %s", exc)
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            logger.warning("Google News RSS parse error: %s", exc)
            return []

        results: list[ArticleDTO] = []
        for item in root.iter("item"):
            if len(results) >= max_results:
                break
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            # Title often "Headline - Publisher"
            source_name = title.split(" - ")[-1].strip() if " - " in title else "Google News"

            dto = ArticleDTO(
                title=title,
                source=source_name,
                url=link,
                published_at=pub,
                description=description,
                credibility_weight=get_weight(source_name),
                is_trusted=is_trusted(source_name),
            )
            if dto.title and dto.url:
                results.append(dto)

        logger.info("Google News RSS returned %d articles for query=%r", len(results), search_q[:60])
        return results
