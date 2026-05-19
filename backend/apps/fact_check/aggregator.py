"""
Fact-check aggregator.

Fans out a search query to all registered source connectors, collects
results, deduplicates by URL, enriches with credibility metadata, and
returns a flat list of article dicts ready for the scoring engine.

Usage
─────
    from apps.fact_check.aggregator import search_all_sources

    articles = search_all_sources(query="climate change IPCC report", max_results=5)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import Type

from apps.fact_check.credibility import enrich_articles
from apps.fact_check.exceptions import FactCheckError, RateLimitError
from apps.fact_check.sources.base import BaseSource, ArticleDTO
from django.conf import settings
from apps.fact_check.sources.gnews import GNewsSource
from apps.fact_check.sources.google_news_rss import GoogleNewsRSSSource

logger = logging.getLogger(__name__)

# Only two connectors: GNews (API) + Google News RSS (trusted wire headlines).
# Wikipedia / DuckDuckGo removed — encyclopaedic matches inflated false confidence.
def _build_registry() -> list[Type[BaseSource]]:
    sources: list[Type[BaseSource]] = [GoogleNewsRSSSource]
    if getattr(settings, "GNEWS_API_KEY", ""):
        sources.insert(0, GNewsSource)
    return sources[:2]


_REGISTRY: list[Type[BaseSource]] = _build_registry()

# Per-source fan-out timeout (seconds)
_FAN_OUT_TIMEOUT = 15


def search_all_sources(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    """
    Query all registered connectors concurrently and return a merged,
    deduplicated list of article dicts.

    Each dict has the shape:
        {
          "title":              str,
          "source":             str,
          "url":                str,
          "published_at":       str,   # ISO 8601
          "description":        str,
          "credibility_weight": float,
          "is_trusted":         bool,
          "source_type":        str,   # connector slug
        }

    A source that raises RateLimitError is skipped with a warning but does
    not abort the fan-out — other connectors continue.
    """
    if not query or not query.strip():
        logger.warning("aggregator.search_all_sources called with empty query.")
        return []

    results: list[dict] = []
    seen_urls: set[str] = set()
    rate_limited: list[str] = []

    with ThreadPoolExecutor(max_workers=len(_REGISTRY) or 1) as pool:
        future_to_slug = {
            pool.submit(_safe_search, cls, query, max_results): cls.slug
            for cls in _REGISTRY
        }

        for future in as_completed(future_to_slug, timeout=_FAN_OUT_TIMEOUT):
            slug = future_to_slug[future]
            try:
                articles, was_rate_limited = future.result()
                if was_rate_limited:
                    rate_limited.append(slug)
                for art in articles:
                    if art["url"] not in seen_urls:
                        seen_urls.add(art["url"])
                        results.append(art)
            except FuturesTimeout:
                logger.warning("Source '%s' timed out during fan-out.", slug)
            except Exception as exc:
                logger.error("Unexpected error from source '%s': %s", slug, exc)

    if rate_limited:
        logger.warning("Rate-limited sources (skipped): %s", rate_limited)

    # Sort by credibility weight descending, then by published date descending
    results.sort(
        key=lambda a: (a.get("credibility_weight", 0), a.get("published_at", "")),
        reverse=True,
    )

    logger.info(
        "Aggregator: %d unique articles from %d source(s) for query=%r",
        len(results), len(_REGISTRY), query[:60],
    )
    return results


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _safe_search(
    source_cls: Type[BaseSource],
    query: str,
    max_results: int,
) -> tuple[list[dict], bool]:
    """
    Instantiate and call a source connector, converting ArticleDTOs to dicts.
    Returns (articles, was_rate_limited).
    """
    source = source_cls()
    was_rate_limited = False

    try:
        dtos: list[ArticleDTO] = source.search(query, max_results=max_results)
        articles = [source.to_dict(dto) for dto in dtos]
        return articles, False

    except RateLimitError as exc:
        logger.warning(
            "Rate limit hit for source '%s': %s", source.slug, exc.user_message
        )
        return [], True

    except FactCheckError as exc:
        logger.warning(
            "FactCheckError from source '%s': %s", source.slug, exc.detail
        )
        return [], False
