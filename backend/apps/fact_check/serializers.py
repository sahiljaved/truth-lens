from rest_framework import serializers


# ──────────────────────────────────────────────────────────────────────────────
# Input serializers
# ──────────────────────────────────────────────────────────────────────────────

class NewsSearchSerializer(serializers.Serializer):
    """
    Input for POST /api/fact-check/search/
    Accepts a query string and optional tuning parameters.
    """
    query = serializers.CharField(
        min_length=3,
        max_length=500,
        help_text="Text to search for in news sources.",
    )
    max_results = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=10,
        help_text="Number of articles to return (1–10, default 5).",
    )
    language = serializers.CharField(
        required=False,
        default="en",
        max_length=5,
        help_text="ISO 639-1 language code (default 'en').",
    )

    def validate_query(self, value):
        return value.strip()


class VerifyTextSerializer(serializers.Serializer):
    """
    Input for POST /api/fact-check/verify/
    Accepts extracted text and an optional list of pre-fetched articles.
    When `articles` is omitted the endpoint fetches from GNews automatically.
    """
    extracted_text = serializers.CharField(
        min_length=10,
        max_length=50_000,
        help_text="The claim / extracted content to verify.",
    )
    articles = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text=(
            "Optional pre-fetched articles. "
            "If omitted, the server queries GNews automatically."
        ),
    )

    def validate_extracted_text(self, value):
        return value.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Output serializers (for documentation / response shaping)
# ──────────────────────────────────────────────────────────────────────────────

class ArticleSerializer(serializers.Serializer):
    title = serializers.CharField()
    source = serializers.CharField()
    url = serializers.URLField()
    published_at = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    credibility_weight = serializers.FloatField()
    is_trusted = serializers.BooleanField()
    source_type = serializers.CharField(required=False)


class VerificationOutputSerializer(serializers.Serializer):
    confidence_score = serializers.FloatField()
    verdict = serializers.CharField()
    summary = serializers.CharField()
    sources = serializers.ListField(child=serializers.DictField())
    flags = serializers.ListField(child=serializers.DictField())
    keyword_count = serializers.IntegerField()
    raw_score = serializers.FloatField()
