"""
Keyword extraction module.

Extracts the most significant words from a text for use in the similarity
and scoring pipeline.  Deliberately dependency-free — no NLTK, spaCy, or
transformers required.

Strategy
────────
1. Lowercase and tokenise on word boundaries.
2. Remove stopwords (built-in English set).
3. Remove tokens shorter than MIN_TOKEN_LEN characters.
4. Count frequencies and return the top MAX_KEYWORDS by frequency.
"""

from __future__ import annotations

import re
from collections import Counter

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

MIN_TOKEN_LEN = 3
MAX_KEYWORDS = 30

# Compact English stopword list — no external dependency needed
_STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while",
    "who", "who's", "whom", "why", "why's", "will", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
    "yours", "yourself", "yourselves", "said", "says", "also", "via", "new",
    "may", "one", "two", "three", "many", "much", "well", "just", "now",
    "still", "even", "back", "use", "used", "make", "made", "take", "taken",
    "come", "came", "good", "first", "last", "long", "since", "per",
    "can", "will", "has", "have", "had", "been", "being", "day", "year",
    "time", "week", "month", "today", "ago",
})


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def extract_keywords(text: str, max_keywords: int = MAX_KEYWORDS) -> set[str]:
    """
    Extract the most frequent meaningful words from `text`.

    Returns a set of lowercase keyword strings.
    """
    if not text:
        return set()

    tokens = _tokenise(text)
    tokens = [t for t in tokens if t not in _STOPWORDS and len(t) >= MIN_TOKEN_LEN]

    if not tokens:
        return set()

    counts = Counter(tokens)
    top = counts.most_common(max_keywords)
    return {word for word, _ in top}


def extract_keywords_ranked(
    text: str, max_keywords: int = MAX_KEYWORDS
) -> list[tuple[str, int]]:
    """
    Like `extract_keywords` but returns a list of (word, frequency) tuples
    sorted by frequency descending.  Useful for debugging / logging.
    """
    if not text:
        return []

    tokens = _tokenise(text)
    tokens = [t for t in tokens if t not in _STOPWORDS and len(t) >= MIN_TOKEN_LEN]

    if not tokens:
        return []

    return Counter(tokens).most_common(max_keywords)


def keyword_overlap_count(keywords: set[str], target_text: str) -> int:
    """
    Count how many keywords from `keywords` appear in `target_text`.

    Args:
        keywords:    Set of lowercase keyword strings (from extract_keywords).
        target_text: Article title + description text to search in.

    Returns:
        Integer count of matching keywords.
    """
    if not keywords or not target_text:
        return 0

    target_words = set(_tokenise(target_text))
    return len(keywords & target_words)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _tokenise(text: str) -> list[str]:
    """Lowercase and split on non-alphanumeric boundaries."""
    return re.findall(r"[a-zA-Z0-9]+", text.lower())
