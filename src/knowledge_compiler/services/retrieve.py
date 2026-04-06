from pathlib import Path

from knowledge_compiler.retrieval.query_tokens import MatchMode, query_token_set
from knowledge_compiler.retrieval.rerank import diversify_hits
from knowledge_compiler.retrieval.sqlite_index import SqliteChunkIndex
from knowledge_compiler.schemas import EvidencePack
from knowledge_compiler.services.runs import record_retrieve_run
from knowledge_compiler.storage import WorkspaceStore


def retrieve_evidence(
    *,
    query: str,
    store: WorkspaceStore,
    limit: int = 5,
    match_mode: str = "and",
    candidate_pool: int | None = None,
    max_chunks_per_document: int = 2,
) -> EvidencePack:
    index_path = store.settings.indexes_dir / "retrieval.db"
    _require_index(index_path)

    mode = MatchMode.OR if match_mode.lower() == "or" else MatchMode.AND
    pool_size = candidate_pool if candidate_pool is not None else max(limit * 6, 32)
    pool_size = min(max(pool_size, limit), 200)

    index = SqliteChunkIndex(index_path)
    raw_hits = index.search(query, limit=pool_size, match_mode=mode)
    terms = query_token_set(query)
    ranked = diversify_hits(
        list(raw_hits),
        query_terms=terms,
        final_limit=limit,
        max_chunks_per_document=max_chunks_per_document,
    )
    hits = tuple(ranked)
    chunk_ids = tuple(hit.chunk_id for hit in hits)

    topics = store.load_topics()
    claims = store.load_claims()

    chunk_id_set = set(chunk_ids)
    topic_ids = tuple(
        sorted(
            topic.topic_id
            for topic in topics
            if set(topic.supporting_chunk_ids) & chunk_id_set
        )
    )
    claim_ids = tuple(
        sorted(
            claim.claim_id
            for claim in claims
            if set(claim.supporting_chunk_ids) & chunk_id_set
        )
    )

    evidence_pack = EvidencePack(
        query=query,
        chunk_ids=chunk_ids,
        hits=hits,
        topic_ids=topic_ids,
        claim_ids=claim_ids,
        match_mode=match_mode.lower() if match_mode.lower() in ("and", "or") else "and",
        ranking_strategy="bm25_lexical_diversify",
        candidate_hits_fetched=len(raw_hits),
        max_chunks_per_document=max_chunks_per_document,
    )
    store.persist_evidence_pack(evidence_pack)
    record_retrieve_run(evidence_pack=evidence_pack, store=store)
    return evidence_pack


def _require_index(index_path: Path) -> None:
    if not index_path.exists():
        message = (
            "The local search index does not exist yet. Run "
            "`uv run knowledge-compiler index` first."
        )
        raise FileNotFoundError(message)
