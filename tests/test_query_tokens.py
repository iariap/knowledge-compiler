from knowledge_compiler.retrieval.query_tokens import (
    MatchMode,
    fts_match_expression,
    lexical_token_set,
    query_tokens,
)


def test_query_tokens_splits_on_punctuation_and_hyphens() -> None:
    assert query_tokens("deterministic & chunking!") == ["deterministic", "chunking"]
    assert query_tokens("foo-bar baz") == ["foo", "bar", "baz"]


def test_query_tokens_keeps_unicode_letters() -> None:
    assert query_tokens("Étude résumé") == ["étude", "résumé"]


def test_lexical_token_set_splits_hyphens_for_overlap_with_query() -> None:
    assert lexical_token_set("Deterministic chunking-based design") >= {
        "deterministic",
        "chunking",
        "based",
        "design",
    }


def test_fts_match_expression_joins_terms_with_and() -> None:
    assert fts_match_expression("hello world") == '"hello" AND "world"'
    assert fts_match_expression('say "hi"') == '"say" AND "hi"'


def test_fts_match_expression_or_mode() -> None:
    assert fts_match_expression("hello world", mode=MatchMode.OR) == '"hello" OR "world"'


def test_empty_or_punctuation_only_query_yields_no_fts_expression() -> None:
    assert query_tokens("!!!") == []
    assert fts_match_expression("   ") == ""
