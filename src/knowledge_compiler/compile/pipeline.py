from collections import defaultdict
from dataclasses import dataclass
from itertools import batched
from re import sub

from knowledge_compiler.compile.themes import cluster_topics_lexical
from knowledge_compiler.schemas import (
    Chunk,
    Claim,
    CompileManifest,
    Document,
    Relation,
    TopicMarkdownArtifact,
    TopicManifestEntry,
    TopicPage,
    TopicRecord,
)


@dataclass(frozen=True)
class _StagedTopic:
    document: Document
    topic_page: TopicPage
    chunks: list[Chunk]
    claims: list[Claim]


def compile_knowledge(
    *,
    documents: list[Document],
    chunks: list[Chunk],
) -> tuple[list[TopicRecord], list[TopicMarkdownArtifact], list[Claim], list[Relation], CompileManifest]:
    chunks_by_document: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        chunks_by_document[chunk.document_id].append(chunk)

    staged: list[_StagedTopic] = []
    claims: list[Claim] = []
    relations: list[Relation] = []

    for document in documents:
        document_chunks = sorted(chunks_by_document.get(document.document_id, []), key=lambda chunk: chunk.ordinal)
        if not document_chunks:
            continue

        topic_id = _slugify(f"{document.title}-{document.document_id[-8:]}")
        summary = _summarize_document(document_chunks)
        topic_page = TopicPage(
            topic_id=topic_id,
            title=document.title,
            summary=summary,
            supporting_chunk_ids=tuple(chunk.chunk_id for chunk in document_chunks),
        )

        document_claims = [
            Claim(
                claim_id=f"{topic_id}-claim-{chunk.ordinal:04d}",
                text=_claim_text(chunk.text),
                supporting_chunk_ids=(chunk.chunk_id,),
            )
            for chunk in document_chunks
        ]
        claims.extend(document_claims)
        relations.extend(
            Relation(
                relation_id=f"{topic_id}-relation-{index:04d}",
                subject=topic_id,
                predicate="contains_claim",
                object=claim.claim_id,
                supporting_claim_ids=(claim.claim_id,),
            )
            for index, claim in enumerate(document_claims)
        )
        staged.append(_StagedTopic(document=document, topic_page=topic_page, chunks=document_chunks, claims=document_claims))

    pre_records = [
        TopicRecord(
            topic_id=s.topic_page.topic_id,
            title=s.topic_page.title,
            summary=s.topic_page.summary,
            supporting_chunk_ids=s.topic_page.supporting_chunk_ids,
            document_id=s.document.document_id,
        )
        for s in staged
    ]
    themes, theme_map = cluster_topics_lexical(pre_records)

    topic_records: list[TopicRecord] = []
    markdown_artifacts: list[TopicMarkdownArtifact] = []
    manifest_topics: list[TopicManifestEntry] = []

    for s in staged:
        tid = s.topic_page.topic_id
        theme_id, theme_label = theme_map.get(tid, ("", ""))
        topic_records.append(
            TopicRecord(
                topic_id=tid,
                title=s.topic_page.title,
                summary=s.topic_page.summary,
                supporting_chunk_ids=s.topic_page.supporting_chunk_ids,
                document_id=s.document.document_id,
                theme_id=theme_id,
                theme_label=theme_label,
            )
        )
        markdown_artifacts.append(
            TopicMarkdownArtifact(
                topic_id=tid,
                markdown=_render_topic_markdown(
                    topic=s.topic_page,
                    document=s.document,
                    chunks=s.chunks,
                    claims=s.claims,
                    theme_id=theme_id,
                    theme_label=theme_label,
                ),
            )
        )
        manifest_topics.append(
            TopicManifestEntry(
                topic_id=tid,
                title=s.topic_page.title,
                document_id=s.document.document_id,
                relative_output_path=f"topics/{tid}.md",
                supporting_chunk_ids=s.topic_page.supporting_chunk_ids,
                theme_id=theme_id,
            )
        )

    source_ids = tuple(sorted({document.source_id for document in documents}))
    manifest = CompileManifest(
        topic_count=len(topic_records),
        claim_count=len(claims),
        relation_count=len(relations),
        topics=tuple(manifest_topics),
        source_ids=source_ids,
        source_id=source_ids[0] if len(source_ids) == 1 else "multi-source",
        themes=themes,
        theme_clustering="lexical-jaccard-v1",
    )
    return topic_records, markdown_artifacts, claims, relations, manifest


def _summarize_document(chunks: list[Chunk]) -> str:
    first_chunk = chunks[0].text.strip()
    return first_chunk[:240].strip()


def _claim_text(text: str) -> str:
    collapsed = " ".join(text.split())
    sentence, _, _ = collapsed.partition(". ")
    return sentence.strip(". ") or collapsed[:200]


def _render_topic_markdown(
    *,
    topic: TopicPage,
    document: Document,
    chunks: list[Chunk],
    claims: list[Claim],
    theme_id: str = "",
    theme_label: str = "",
) -> str:
    chunk_sections = []
    for chunk_group, claim in zip(batched(chunks, 1), claims, strict=False):
        chunk = chunk_group[0]
        chunk_sections.append(
            "\n".join(
                [
                    f"### Chunk {chunk.ordinal}",
                    f"- Chunk ID: `{chunk.chunk_id}`",
                    f"- Lines: `{chunk.provenance.start_line}-{chunk.provenance.end_line}`",
                    f"- Claim: {claim.text}",
                    "",
                    chunk.text,
                ]
            )
        )

    body = "\n\n".join(chunk_sections)
    theme_block: list[str] = []
    if theme_label or theme_id:
        theme_block = [
            "## Theme",
            "",
            f"- Label: {theme_label or '—'}",
            f"- Theme ID: `{theme_id}`" if theme_id else "",
            "",
        ]

    return "\n".join(
        [
            f"# {topic.title}",
            "",
            f"- Topic ID: `{topic.topic_id}`",
            f"- Document: `{document.relative_path}`",
            "",
            *theme_block,
            "## Summary",
            "",
            topic.summary,
            "",
            "## Evidence",
            "",
            body,
            "",
        ]
    )


def _slugify(value: str) -> str:
    normalized = sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "topic"
