"""
Abstract base class for all fact-check source connectors.

Every connector must implement `search(query)` and expose its `slug`
(used as the identifier in aggregator results and logs).

Implementing a new connector is as simple as:

    class MySource(BaseSource):
        slug = "mysource"

        def search(self, query: str, max_results: int = 5) -> list[dict]:
            ...
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ArticleDTO:
    """
    Normalised article representation returned by every source connector.
    All fields are strings so they can be safely JSON-serialised.
    """
    title: str
    source: str
    url: str
    published_at: str          # ISO 8601 string
    description: str = ""
    credibility_weight: float = 0.40
    is_trusted: bool = False


class BaseSource(ABC):
    """Abstract fact-check source connector."""

    #: Unique slug, used in logs and as the `source_type` tag on results.
    slug: str = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[ArticleDTO]:
        """
        Search the source for content related to `query`.

        Args:
            query:       Cleaned search string.
            max_results: Maximum number of articles to return.

        Returns:
            List of ArticleDTO instances (may be empty on no results).

        Raises:
            FactCheckError subclasses on hard failures (rate-limit, auth, etc.).
        """
        raise NotImplementedError

    def to_dict(self, article: ArticleDTO) -> dict:
        """Serialise an ArticleDTO to the canonical API response dict."""
        return {
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at,
            "description": article.description,
            "credibility_weight": article.credibility_weight,
            "is_trusted": article.is_trusted,
            "source_type": self.slug,
        }
