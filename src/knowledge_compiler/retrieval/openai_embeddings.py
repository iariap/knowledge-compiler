"""Batch embeddings via OpenAI-compatible /v1/embeddings (urllib, no extra deps)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch_embedding_vectors(
    *,
    texts: list[str],
    api_key: str,
    base_url: str,
    model: str,
    timeout_s: int = 120,
) -> list[list[float]]:
    if not texts:
        return []
    url = f"{base_url.rstrip('/')}/v1/embeddings"
    body = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        message = f"Embeddings API HTTP {error.code}: {detail}"
        raise OSError(message) from error
    except URLError as error:
        message = f"Embeddings API network error: {error}"
        raise OSError(message) from error

    rows = payload.get("data") or []
    ordered = sorted(rows, key=lambda row: int(row.get("index", 0)))
    out: list[list[float]] = []
    for row in ordered:
        emb = row.get("embedding")
        if not isinstance(emb, list):
            message = f"Unexpected embedding row: {row!r}"
            raise ValueError(message)
        out.append([float(x) for x in emb])
    if len(out) != len(texts):
        message = f"Embedding count mismatch: expected {len(texts)}, got {len(out)}"
        raise ValueError(message)
    return out
