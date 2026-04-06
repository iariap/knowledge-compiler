"""Shared query tokenization for FTS and query-aware context scoring."""

from __future__ import annotations

import re
from enum import Enum


class MatchMode(str, Enum):
    """How multiple query terms are combined in FTS5 MATCH."""

    AND = "and"
    OR = "or"


STOPWORDS = frozenset(
    {
        "a",
        "an",
        "about",
        "and",
        "are",
        "did",
        "do",
        "for",
        "how",
        "i",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "where",
        "with",
        "write",
        "wrote",
    }
)


def query_tokens(query: str) -> list[str]:
    """Return search terms derived from the raw query (Unicode word characters, stopwords dropped)."""
    raw_terms = [term.casefold() for term in re.findall(r"\w+", query)]
    filtered_terms = [term for term in raw_terms if term not in STOPWORDS]
    selected_terms = filtered_terms or [term for term in raw_terms if len(term) > 1]
    return selected_terms


def query_token_set(query: str) -> set[str]:
    return set(query_tokens(query))


def lexical_token_set(text: str) -> set[str]:
    """Casefolded word tokens from arbitrary text (corpus side), for overlap with `query_token_set`."""
    return {term.casefold() for term in re.findall(r"\w+", text)}


def fts_match_expression(query: str, *, mode: MatchMode = MatchMode.AND) -> str:
    """Build an FTS5 MATCH expression; terms are quoted phrases, combined with AND or OR."""
    terms = query_tokens(query)
    if not terms:
        return ""
    parts = [f'"{_escape_fts5_term(term)}"' for term in terms]
    joiner = " OR " if mode is MatchMode.OR else " AND "
    return joiner.join(parts)


def _escape_fts5_term(term: str) -> str:
    return term.replace('"', '""')
