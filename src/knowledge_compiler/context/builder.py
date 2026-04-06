from dataclasses import dataclass

from knowledge_compiler.retrieval.query_tokens import lexical_token_set, query_token_set
from knowledge_compiler.schemas import ContextPack, ContextSnippet, EvidencePack


@dataclass(frozen=True)
class _SnippetCandidate:
    chunk_id: str
    relative_path: str
    start_line: int
    end_line: int
    text: str
    source_score: float
    matched_terms: int


def _estimate_tokens(text: str) -> int:
    """Rough heuristic (~4 chars per token for Latin-heavy text)."""
    return max(1, (len(text) + 3) // 4)


def build_context_pack(*, evidence_pack: EvidencePack, max_chars: int) -> ContextPack:
    query_terms = query_token_set(evidence_pack.query)
    candidates = _build_candidates(evidence_pack=evidence_pack, query_terms=query_terms)
    snippets: list[ContextSnippet] = []
    used_chars = 0
    selected_chunk_ids: list[str] = []
    seen_texts: set[str] = set()

    for candidate in candidates:
        normalized_candidate = " ".join(candidate.text.split()).casefold()
        if not normalized_candidate or normalized_candidate in seen_texts:
            continue

        remaining = max_chars - used_chars
        if remaining <= 0:
            break

        selected_text = candidate.text[:remaining].rstrip()
        if not selected_text:
            continue

        snippets.append(
            ContextSnippet(
                chunk_id=candidate.chunk_id,
                relative_path=candidate.relative_path,
                start_line=candidate.start_line,
                end_line=candidate.end_line,
                text=selected_text,
                score=candidate.source_score,
                matched_terms=candidate.matched_terms,
            )
        )
        seen_texts.add(normalized_candidate)
        if candidate.chunk_id not in selected_chunk_ids:
            selected_chunk_ids.append(candidate.chunk_id)
        used_chars += len(selected_text)

    selected_topics = tuple(
        topic_id for topic_id in evidence_pack.topic_ids if topic_id
    )
    selected_claims = tuple(
        claim_id for claim_id in evidence_pack.claim_ids if claim_id
    )

    token_estimate = sum(_estimate_tokens(s.text) for s in snippets) + 4 * len(snippets)

    return ContextPack(
        query=evidence_pack.query,
        source_hit_count=len(evidence_pack.hits),
        selection_strategy="query-aware-multi-snippet-v2",
        max_chars=max_chars,
        used_chars=used_chars,
        estimated_input_tokens=token_estimate,
        chunk_ids=tuple(selected_chunk_ids),
        topic_ids=selected_topics,
        claim_ids=selected_claims,
        snippets=tuple(snippets),
    )


def _build_candidates(
    *,
    evidence_pack: EvidencePack,
    query_terms: set[str],
) -> list[_SnippetCandidate]:
    candidates: list[_SnippetCandidate] = []
    for hit in evidence_pack.hits:
        sentences = _split_sentences(hit.text)
        if not sentences:
            continue

        hit_candidates = [
            _SnippetCandidate(
                chunk_id=hit.chunk_id,
                relative_path=hit.relative_path,
                start_line=hit.start_line,
                end_line=hit.end_line,
                text=sentence,
                source_score=hit.score,
                matched_terms=_matched_terms(sentence, query_terms),
            )
            for sentence in sentences
        ]
        best_for_hit = sorted(
            hit_candidates,
            key=lambda candidate: (
                candidate.matched_terms,
                candidate.source_score,
                -len(candidate.text),
            ),
            reverse=True,
        )[0]
        candidates.append(best_for_hit)

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.matched_terms,
            candidate.source_score,
            -len(candidate.text),
        ),
        reverse=True,
    )


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    sentences = [sentence.strip().strip(".") for sentence in normalized.split(". ") if sentence.strip()]
    return sentences or ([normalized] if normalized else [])


def _matched_terms(sentence: str, query_terms: set[str]) -> int:
    return len(query_terms & lexical_token_set(sentence))
