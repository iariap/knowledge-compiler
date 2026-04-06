from knowledge_compiler.retrieval.query_tokens import lexical_token_set, query_token_set
from knowledge_compiler.schemas import AnswerCitation, ContextPack, QueryAnswer
from knowledge_compiler.services.context import build_query_context
from knowledge_compiler.services.runs import record_ask_run
from knowledge_compiler.storage import WorkspaceStore


def ask_workspace(
    *,
    query: str,
    store: WorkspaceStore,
    limit: int = 5,
    match_mode: str = "and",
    candidate_pool: int | None = None,
    max_chunks_per_document: int = 2,
) -> QueryAnswer:
    context_pack = build_query_context(
        query=query,
        store=store,
        limit=limit,
        match_mode=match_mode,
        candidate_pool=candidate_pool,
        max_chunks_per_document=max_chunks_per_document,
    )
    hits = context_pack.snippets

    if not hits:
        answer = QueryAnswer(
            query=query,
            answer_text="No grounded evidence was found for that query in the current workspace.",
            citations=(),
            evidence=(),
        )
        store.persist_query_answer(answer)
        record_ask_run(answer=answer, store=store, context_pack=context_pack)
        return answer

    answer = QueryAnswer(
        query=query,
        answer_text=_build_grounded_answer(query=query, context_pack=context_pack),
        citations=tuple(
            AnswerCitation(
                chunk_id=hit.chunk_id,
                relative_path=hit.relative_path,
                start_line=hit.start_line,
                end_line=hit.end_line,
            )
            for hit in hits
        ),
        evidence=(),
    )
    store.persist_query_answer(answer)
    record_ask_run(answer=answer, store=store, context_pack=context_pack)
    return answer


def _build_grounded_answer(*, query: str, context_pack: ContextPack) -> str:
    query_terms = query_token_set(query)
    sentences: list[str] = []
    for hit in context_pack.snippets:
        candidate = _best_matching_sentence(hit.text, query_terms)
        if candidate and candidate not in sentences:
            sentences.append(candidate)

    return " ".join(sentences[:3])


def _best_matching_sentence(text: str, query_terms: set[str]) -> str:
    normalized = " ".join(text.split())
    sentences = [sentence.strip() for sentence in normalized.split(". ") if sentence.strip()]
    ranked = sorted(
        sentences,
        key=lambda sentence: _sentence_score(sentence, query_terms),
        reverse=True,
    )
    return ranked[0].strip(". ") if ranked else normalized[:240]


def _sentence_score(sentence: str, query_terms: set[str]) -> tuple[int, int]:
    overlap = len(query_terms & lexical_token_set(sentence))
    return overlap, -len(sentence)
