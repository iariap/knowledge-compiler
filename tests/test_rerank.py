from knowledge_compiler.retrieval.rerank import diversify_hits
from knowledge_compiler.schemas import SearchHit


def test_diversify_prefers_one_chunk_per_document_before_backfill() -> None:
    hits = [
        SearchHit(
            chunk_id=f"c{i}",
            document_id="doc-a" if i < 3 else "doc-b",
            relative_path="a.txt",
            score=1.0 - i * 0.01,
            text=f"term{i} content",
            start_line=1,
            end_line=1,
        )
        for i in range(5)
    ]
    terms = {"term0", "content"}
    out = diversify_hits(
        hits,
        query_terms=terms,
        final_limit=2,
        max_chunks_per_document=1,
    )
    assert len(out) == 2
    assert {h.document_id for h in out} == {"doc-a", "doc-b"}
