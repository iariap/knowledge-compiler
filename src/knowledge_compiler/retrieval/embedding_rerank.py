"""Reorder FTS hits by cosine similarity to query embeddings (in-memory)."""

from __future__ import annotations

import math
import os

from knowledge_compiler.retrieval.openai_embeddings import fetch_embedding_vectors
from knowledge_compiler.schemas import SearchHit

_MAX_EMBED_CHARS = 8_000


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embedding_rerank_hits(
    hits: list[SearchHit],
    *,
    query: str,
    api_key: str,
    base_url: str,
    model: str,
) -> list[SearchHit]:
    if not hits:
        return []
    texts = [query] + [hit.text[:_MAX_EMBED_CHARS] for hit in hits]
    vectors = fetch_embedding_vectors(texts=texts, api_key=api_key, base_url=base_url, model=model)
    query_vec, *hit_vecs = vectors
    scored: list[tuple[float, SearchHit]] = []
    for hit, vec in zip(hits, hit_vecs, strict=True):
        sim = _cosine(query_vec, vec)
        scored.append((sim, hit.model_copy(update={"score": float(sim)})))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored]


def default_embedding_model() -> str:
    return os.environ.get("KNOWLEDGE_COMPILER_EMBEDDING_MODEL", "text-embedding-3-small").strip() or (
        "text-embedding-3-small"
    )
