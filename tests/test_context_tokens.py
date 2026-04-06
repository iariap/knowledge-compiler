from knowledge_compiler.context.builder import build_context_pack
from knowledge_compiler.schemas import EvidencePack, SearchHit


def test_build_context_pack_respects_max_tokens() -> None:
    hits = tuple(
        SearchHit(
            chunk_id=f"c{i}",
            document_id=f"d{i}",
            relative_path=f"f{i}.md",
            score=1.0,
            text="word " * 200,
            start_line=1,
            end_line=5,
        )
        for i in range(3)
    )
    pack = EvidencePack(query="word", chunk_ids=tuple(h.chunk_id for h in hits), hits=hits)
    ctx = build_context_pack(evidence_pack=pack, max_chars=50_000, max_tokens=30)
    assert ctx.max_tokens == 30
    assert ctx.used_tokens <= 30
    assert ctx.used_chars <= 50_000
