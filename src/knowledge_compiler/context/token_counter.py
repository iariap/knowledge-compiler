"""Token counting: prefer tiktoken when installed, else char heuristic."""

from __future__ import annotations

_DEFAULT_ENCODING = "cl100k_base"


def count_tokens(text: str, *, encoding_name: str | None = None) -> int:
    if not text:
        return 0
    name = encoding_name or _DEFAULT_ENCODING
    try:
        import tiktoken

        enc = tiktoken.get_encoding(name)
        return len(enc.encode(text))
    except Exception:
        return max(1, (len(text) + 3) // 4)


def clip_text_to_token_budget(text: str, max_tokens: int, *, encoding_name: str | None = None) -> str:
    if max_tokens <= 0 or not text:
        return ""
    if count_tokens(text, encoding_name=encoding_name) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count_tokens(text[:mid], encoding_name=encoding_name) <= max_tokens:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip()
