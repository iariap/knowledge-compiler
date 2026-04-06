"""Post-retrieval reranking and diversification over lexical search hits."""

from __future__ import annotations

from collections import defaultdict

from knowledge_compiler.retrieval.query_tokens import lexical_token_set
from knowledge_compiler.schemas import SearchHit


def diversify_hits(
    hits: list[SearchHit],
    *,
    query_terms: set[str],
    final_limit: int,
    max_chunks_per_document: int,
    lexical_weight: float = 0.12,
) -> list[SearchHit]:
    """Rerank by BM25 score plus lexical overlap, then greedily cap chunks per document."""
    if not hits:
        return []

    scored: list[tuple[float, SearchHit]] = []
    for hit in hits:
        overlap = len(query_terms & lexical_token_set(hit.text))
        composite = float(hit.score) + lexical_weight * overlap
        scored.append((composite, hit))

    scored.sort(key=lambda item: item[0], reverse=True)

    picked: list[SearchHit] = []
    seen_ids: set[str] = set()
    per_document: dict[str, int] = defaultdict(int)

    def try_take(hit: SearchHit, *, enforce_cap: bool) -> None:
        if hit.chunk_id in seen_ids:
            return
        if enforce_cap and per_document[hit.document_id] >= max_chunks_per_document:
            return
        picked.append(hit)
        seen_ids.add(hit.chunk_id)
        per_document[hit.document_id] += 1

    for _, hit in scored:
        if len(picked) >= final_limit:
            break
        try_take(hit, enforce_cap=True)

    if len(picked) < final_limit:
        for _, hit in scored:
            if len(picked) >= final_limit:
                break
            try_take(hit, enforce_cap=False)

    return picked[:final_limit]
