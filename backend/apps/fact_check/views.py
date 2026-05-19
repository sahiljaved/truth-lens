"""
Fact-check API views.

Endpoints
─────────
  POST /api/fact-check/search/   — query GNews, return top N articles
  POST /api/fact-check/verify/   — score extracted text against articles
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.fact_check.aggregator import search_all_sources
from apps.fact_check.exceptions import (
    FactCheckError,
    InvalidAPIKeyError,
    RateLimitError,
    SearchTimeoutError,
)
from apps.scoring.engine import compute as compute_score
from apps.scoring.response_builder import build as build_response

from core.security import public_error_payload
from .serializers import NewsSearchSerializer, VerifyTextSerializer

logger = logging.getLogger(__name__)


class NewsSearchView(APIView):
    """
    POST /api/fact-check/search/

    Query registered news sources for articles related to the given text.
    Returns up to `max_results` articles sorted by credibility weight.

    Request JSON:
        {
          "query":       string,            // required, 3–500 chars
          "max_results": int,               // optional, 1–10 (default 5)
          "language":    string             // optional, default "en"
        }

    Response 200:
        {
          "query":        string,
          "total":        int,
          "articles":     [ { title, source, url, published_at,
                              description, credibility_weight, is_trusted } ]
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NewsSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        query: str = serializer.validated_data["query"]
        max_results: int = serializer.validated_data["max_results"]

        try:
            articles = search_all_sources(query=query, max_results=max_results)
        except RateLimitError as exc:
            logger.warning("Rate limit hit: %s", exc.user_message)
            headers = {}
            if exc.retry_after:
                headers["Retry-After"] = str(exc.retry_after)
            return Response(
                {
                    "error": exc.user_message,
                    "code": "RATE_LIMIT_EXCEEDED",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
            )
        except InvalidAPIKeyError as exc:
            logger.error("Invalid API key: %s", exc.detail)
            return Response(
                public_error_payload(
                    "News search is temporarily unavailable.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    code="SERVICE_UNAVAILABLE",
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except SearchTimeoutError as exc:
            logger.warning("Search timeout: %s", exc.detail)
            return Response(
                {"error": exc.user_message, "code": "SOURCE_TIMEOUT"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except FactCheckError as exc:
            logger.error("Fact-check source error: %s", exc.detail)
            return Response(
                {"error": exc.user_message},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "query": query,
                "total": len(articles),
                "articles": articles,
            },
            status=status.HTTP_200_OK,
        )


class VerifyTextView(APIView):
    """
    POST /api/fact-check/verify/

    Score extracted claim text against news articles.
    If `articles` is not provided, the server fetches from GNews automatically.

    Request JSON:
        {
          "extracted_text": string,         // required, 10–50 000 chars
          "articles":       [ ... ]         // optional, pre-fetched article dicts
        }

    Response 200:
        {
          "confidence_score": float,        // 0.0–1.0
          "verdict":          string,       // LIKELY_TRUE | UNCERTAIN | LIKELY_FALSE | UNVERIFIABLE
          "summary":          string,
          "sources":          [ ... ],
          "flags":            [ { type, severity, detail } ],
          "keyword_count":    int,
          "raw_score":        float
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyTextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extracted_text: str = serializer.validated_data["extracted_text"]
        articles: list = serializer.validated_data.get("articles") or []

        # Auto-fetch from GNews when no articles were provided
        if not articles:
            try:
                articles = search_all_sources(query=extracted_text, max_results=5)
            except RateLimitError as exc:
                logger.warning("Rate limit during verify auto-fetch: %s", exc.user_message)
                return Response(
                    {"error": exc.user_message, "code": "RATE_LIMIT_EXCEEDED"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            except FactCheckError as exc:
                logger.warning(
                    "Source error during verify auto-fetch (continuing with 0 articles): %s",
                    exc.detail,
                )
                articles = []

        # Run scoring engine
        output = compute_score(extracted_text=extracted_text, articles=articles)
        payload = build_response(output)

        return Response(payload, status=status.HTTP_200_OK)
