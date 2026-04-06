from knowledge_compiler.schemas import AnswerCitation, AnswerTrace, QueryAnswer, QueryRun
from knowledge_compiler.storage import WorkspaceStore


def resolve_ask_run(*, store: WorkspaceStore, run_id: str) -> QueryRun:
    if not run_id.strip():
        message = "run id must be non-empty"
        raise ValueError(message)
    needle = run_id.strip()
    runs = store.load_query_runs()
    ask_runs = [run for run in runs if run.command == "ask"]
    exact = [run for run in ask_runs if run.run_id == needle]
    if len(exact) == 1:
        return exact[0]
    prefixed = [run for run in ask_runs if run.run_id.startswith(needle)]
    if len(prefixed) == 1:
        return prefixed[0]
    if len(prefixed) > 1:
        sample = ", ".join(r.run_id for r in prefixed[:8])
        message = f"Ambiguous run id {needle!r}; matches include: {sample}"
        raise ValueError(message)
    message = f"No ask run found for id {needle!r}. Use `runs` to list recent ids."
    raise KeyError(message)


def trace_ask_run(*, store: WorkspaceStore, run_id: str) -> AnswerTrace:
    run = resolve_ask_run(store=store, run_id=run_id)
    if not run.citation_chunk_ids:
        message = (
            "This ask run has no stored citation ids (likely recorded before this feature). "
            "Run a new `ask` query, or use `trace` without --run for the last answer file."
        )
        raise ValueError(message)

    chunks_by_id = {chunk.chunk_id: chunk for chunk in store.load_chunks()}
    citations: list[AnswerCitation] = []
    cited_chunks = []
    for chunk_id in run.citation_chunk_ids:
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            continue
        cited_chunks.append(chunk)
        citations.append(
            AnswerCitation(
                chunk_id=chunk.chunk_id,
                relative_path=chunk.provenance.relative_path,
                start_line=chunk.provenance.start_line,
                end_line=chunk.provenance.end_line,
            )
        )

    answer = QueryAnswer(
        query=run.query,
        answer_text=run.answer_text or run.answer_preview or "",
        citations=tuple(citations),
        evidence=(),
    )
    return AnswerTrace(answer=answer, cited_chunks=tuple(cited_chunks))
