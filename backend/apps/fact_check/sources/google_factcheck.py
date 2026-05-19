"""
Google Fact Check Tools API connector.

Docs: https://developers.google.com/fact-check/tools/api
Requires GOOGLE_FACTCHECK_API_KEY in settings.
"""

from __future__ import annotations

import logging

from django.conf import settings

from apps.fact_check.credibility import get_weight, is_trusted
from apps.fact_check.exceptions import InvalidAPIKeyError, ParseError, SourceUnavailableError
from core.http import get
from core.search_query import build_search_query
from .base import ArticleDTO, BaseSource

logger = logging.getLogger(__name__)

_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckSource(BaseSource):
    slug = "google_factcheck"

    def __init__(self):
        self._api_key = getattr(settings, "GOOGLE_FACTCHECK_API_KEY", "")
        self._timeout = getattr(settings, "SOURCE_REQUEST_TIMEOUT", 10)

    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        if not self._api_key:
            return []

        search_q = build_search_query(query) or query[:200].strip()
        if not search_q:
            return []

        try:
            resp = get(
                _API_URL,
                params={
                    "query": search_q,
                    "key": self._api_key,
                    "languageCode": "en",
                    "pageSize": min(max_results, 10),
                },
                timeout=self._timeout,
            )
        except Exception as exc:
            raise SourceUnavailableError(
                "Could not reach Google Fact Check API.",
                detail=str(exc),
            )

        if resp.status_code in (401, 403):
            raise InvalidAPIKeyError(
                "Fact-check service is temporarily unavailable.",
                detail=f"HTTP {resp.status_code}: {resp.text[:200]}",
            )

        if resp.status_code != 200:
            raise SourceUnavailableError(
                f"Google Fact Check API error (HTTP {resp.status_code}).",
                detail=resp.text[:300],
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise ParseError("Google Fact Check returned invalid JSON.", detail=str(exc))

        return self._parse(data, max_results)

    def _parse(self, data: dict, max_results: int) -> list[ArticleDTO]:
        claims = data.get("claims") or []
        results: list[ArticleDTO] = []

        for claim in claims[:max_results]:
            claim_text = (claim.get("text") or "").strip()
            reviews = claim.get("claimReview") or []
            for review in reviews:
                publisher = review.get("publisher") or {}
                source_name = publisher.get("name") or "Google Fact Check"
                url = review.get("url") or publisher.get("site") or ""
                rating = review.get("textualRating") or ""
                title = claim_text[:120] if claim_text else rating or "Fact-check result"
                description = f"{rating}. {claim_text}".strip() if rating else claim_text

                dto = ArticleDTO(
                    title=title,
                    source=source_name,
                    url=url,
                    published_at=review.get("reviewDate", ""),
                    description=description[:500],
                    credibility_weight=max(get_weight(source_name), 0.85),
                    is_trusted=True,
                )
                if dto.title:
                    results.append(dto)
                    break

        logger.info("Google Fact Check returned %d results", len(results))
        return results
