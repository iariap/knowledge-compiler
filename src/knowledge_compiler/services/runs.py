from uuid import uuid4

from knowledge_compiler.schemas import ContextPack, EvidencePack, QueryAnswer, QueryRun
from knowledge_compiler.storage import WorkspaceStore


def record_retrieve_run(*, evidence_pack: EvidencePack, store: WorkspaceStore) -> QueryRun:
    run = QueryRun(
        run_id=_run_id("retrieve", evidence_pack.query),
        command="retrieve",
        query=evidence_pack.query,
        hit_count=len(evidence_pack.hits),
        chunk_count=len(evidence_pack.chunk_ids),
        topic_count=len(evidence_pack.topic_ids),
        claim_count=len(evidence_pack.claim_ids),
    )
    store.append_query_run(run)
    return run


def record_context_run(*, context_pack: ContextPack, store: WorkspaceStore) -> QueryRun:
    run = QueryRun(
        run_id=_run_id("context", context_pack.query),
        command="context",
        query=context_pack.query,
        hit_count=len(context_pack.snippets),
        chunk_count=len(context_pack.chunk_ids),
        topic_count=len(context_pack.topic_ids),
        claim_count=len(context_pack.claim_ids),
        context_chars=context_pack.used_chars,
    )
    store.append_query_run(run)
    return run


def record_ask_run(
    *,
    answer: QueryAnswer,
    store: WorkspaceStore,
    context_pack: ContextPack | None = None,
) -> QueryRun:
    cited_chunks = {citation.chunk_id for citation in answer.citations}
    run = QueryRun(
        run_id=_run_id("ask", answer.query),
        command="ask",
        query=answer.query,
        hit_count=len(answer.citations),
        chunk_count=len(cited_chunks),
        topic_count=len(context_pack.topic_ids) if context_pack is not None else 0,
        claim_count=len(context_pack.claim_ids) if context_pack is not None else 0,
        context_chars=context_pack.used_chars if context_pack is not None else None,
        answer_preview=answer.answer_text[:160],
        answer_text=answer.answer_text,
        citation_chunk_ids=tuple(citation.chunk_id for citation in answer.citations),
    )
    store.append_query_run(run)
    return run


def list_query_runs(*, store: WorkspaceStore, limit: int = 10) -> list[QueryRun]:
    return list(reversed(store.load_query_runs()))[:limit]


def _run_id(command: str, query: str) -> str:
    _ = query  # retained for call-site compatibility; ids must be unique per invocation
    return f"{command}-{uuid4().hex[:12]}"
