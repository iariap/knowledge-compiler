from knowledge_compiler.context import build_context_pack
from knowledge_compiler.schemas import ContextPack
from knowledge_compiler.services.runs import record_context_run
from knowledge_compiler.services.retrieve import retrieve_evidence
from knowledge_compiler.storage import WorkspaceStore


def build_query_context(
    *,
    query: str,
    store: WorkspaceStore,
    limit: int = 5,
    max_chars: int = 1_500,
    match_mode: str = "and",
    candidate_pool: int | None = None,
    max_chunks_per_document: int = 2,
) -> ContextPack:
    evidence_pack = retrieve_evidence(
        query=query,
        store=store,
        limit=limit,
        match_mode=match_mode,
        candidate_pool=candidate_pool,
        max_chunks_per_document=max_chunks_per_document,
    )
    context_pack = build_context_pack(evidence_pack=evidence_pack, max_chars=max_chars)
    store.persist_context_pack(context_pack)
    record_context_run(context_pack=context_pack, store=store)
    return context_pack
