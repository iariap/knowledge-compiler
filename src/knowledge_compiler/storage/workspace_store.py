import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from knowledge_compiler.config import Settings
from knowledge_compiler.schemas import (
    AnswerTrace,
    Chunk,
    ChunkInspection,
    Claim,
    CompileManifest,
    ContextPack,
    Document,
    EvidencePack,
    IngestManifest,
    QueryAnswer,
    QueryRun,
    Relation,
    Source,
    TopicInspection,
    TopicMarkdownArtifact,
    TopicRecord,
    WorkspaceInspection,
)


class WorkspaceStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def settings(self) -> Settings:
        return self._settings

    def ensure_workspace(self) -> None:
        self._settings.raw_dir.mkdir(parents=True, exist_ok=True)
        self._settings.state_dir.mkdir(parents=True, exist_ok=True)
        self._settings.compiled_dir.mkdir(parents=True, exist_ok=True)
        self._settings.indexes_dir.mkdir(parents=True, exist_ok=True)

    def persist_ingest_bundle(
        self,
        *,
        source: Source,
        documents: list[Document],
        chunks: list[Chunk],
        merge: bool = False,
    ) -> IngestManifest:
        state_dir = self._settings.state_dir
        sources_path = state_dir / "sources.json"
        docs_path = state_dir / "documents.jsonl"
        chunks_path = state_dir / "chunks.jsonl"

        if merge and sources_path.exists():
            existing_sources = self.load_sources()
            existing_docs = self.load_documents() if docs_path.exists() else []
            existing_chunks = self.load_chunks() if chunks_path.exists() else []

            kept_sources = [s for s in existing_sources if s.source_id != source.source_id]
            kept_sources.append(source)
            kept_sources.sort(key=lambda s: s.source_id)

            kept_docs = [d for d in existing_docs if d.source_id != source.source_id]
            kept_chunks = [c for c in existing_chunks if c.provenance.source_id != source.source_id]

            kept_doc_ids = {document.document_id for document in kept_docs}
            new_docs = [document for document in documents if document.document_id not in kept_doc_ids]
            new_doc_ids = {document.document_id for document in new_docs}
            new_chunks = [chunk for chunk in chunks if chunk.document_id in new_doc_ids]

            merged_docs = kept_docs + new_docs
            merged_chunks = kept_chunks + new_chunks
            source_ids = tuple(sorted({s.source_id for s in kept_sources}))
            manifest = IngestManifest(
                source_id=source.source_id,
                source_ids=source_ids,
                document_count=len(merged_docs),
                chunk_count=len(merged_chunks),
            )
            self._write_json(sources_path, [s.model_dump(mode="json") for s in kept_sources])
            self._write_jsonl(docs_path, merged_docs)
            self._write_jsonl(chunks_path, merged_chunks)
            self._write_json(state_dir / "ingest-manifest.json", manifest.model_dump(mode="json"))
            return manifest

        source_ids = (source.source_id,)
        manifest = IngestManifest(
            source_id=source.source_id,
            source_ids=source_ids,
            document_count=len(documents),
            chunk_count=len(chunks),
        )
        self._write_json(sources_path, [source.model_dump(mode="json")])
        self._write_jsonl(docs_path, documents)
        self._write_jsonl(chunks_path, chunks)
        self._write_json(state_dir / "ingest-manifest.json", manifest.model_dump(mode="json"))
        return manifest

    def load_sources(self) -> list[Source]:
        payload = self._read_json(self._settings.state_dir / "sources.json")
        if not isinstance(payload, list):
            raise ValueError("sources.json must contain a JSON array")
        return [Source.model_validate(row) for row in payload]

    def load_source(self) -> Source:
        sources = self.load_sources()
        if not sources:
            raise FileNotFoundError("No sources in workspace; run ingest first.")
        return sources[0]

    def load_documents(self) -> list[Document]:
        return self._read_jsonl(self._settings.state_dir / "documents.jsonl", Document)

    def load_chunks(self) -> list[Chunk]:
        return self._read_jsonl(self._settings.state_dir / "chunks.jsonl", Chunk)

    def persist_query_answer(self, answer: QueryAnswer) -> None:
        self._write_json(
            self._settings.state_dir / "last-answer.json",
            answer.model_dump(mode="json"),
        )

    def load_last_answer(self) -> QueryAnswer:
        payload = self._read_json(self._settings.state_dir / "last-answer.json")
        return QueryAnswer.model_validate(payload)

    def append_query_run(self, query_run: QueryRun) -> None:
        path = self._settings.state_dir / "query-runs.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(query_run.model_dump(mode="json"), sort_keys=True))
            handle.write("\n")

    def load_query_runs(self) -> list[QueryRun]:
        path = self._settings.state_dir / "query-runs.jsonl"
        if not path.exists():
            return []
        return self._read_jsonl(path, QueryRun)

    def persist_evidence_pack(self, evidence_pack: EvidencePack) -> None:
        self._write_json(
            self._settings.state_dir / "last-evidence-pack.json",
            evidence_pack.model_dump(mode="json"),
        )

    def load_last_evidence_pack(self) -> EvidencePack:
        payload = self._read_json(self._settings.state_dir / "last-evidence-pack.json")
        return EvidencePack.model_validate(payload)

    def persist_context_pack(self, context_pack: ContextPack) -> None:
        self._write_json(
            self._settings.state_dir / "last-context-pack.json",
            context_pack.model_dump(mode="json"),
        )

    def load_last_context_pack(self) -> ContextPack:
        payload = self._read_json(self._settings.state_dir / "last-context-pack.json")
        return ContextPack.model_validate(payload)

    def load_ingest_manifest(self) -> IngestManifest:
        payload = self._read_json(self._settings.state_dir / "ingest-manifest.json")
        return IngestManifest.model_validate(payload)

    def load_compile_manifest(self) -> CompileManifest:
        payload = self._read_json(self._settings.compiled_dir / "compile-manifest.json")
        return CompileManifest.model_validate(payload)

    def load_claims(self) -> list[Claim]:
        return self._read_jsonl(self._settings.compiled_dir / "claims.jsonl", Claim)

    def load_relations(self) -> list[Relation]:
        return self._read_jsonl(self._settings.compiled_dir / "relations.jsonl", Relation)

    def load_topics(self) -> list[TopicRecord]:
        payload = self._read_json(self._settings.compiled_dir / "topics.json")
        return [TopicRecord.model_validate(row) for row in payload]

    def inspect_workspace(self) -> WorkspaceInspection:
        ingest_manifest = self.load_ingest_manifest()
        compile_manifest = self.load_compile_manifest()
        source_ids = ingest_manifest.source_ids
        display_source = (
            source_ids[0]
            if len(source_ids) == 1
            else "multi-source"
            if source_ids
            else ingest_manifest.source_id
        )
        return WorkspaceInspection(
            source_id=display_source,
            source_ids=source_ids,
            document_count=ingest_manifest.document_count,
            chunk_count=ingest_manifest.chunk_count,
            topic_count=compile_manifest.topic_count,
            claim_count=compile_manifest.claim_count,
            relation_count=compile_manifest.relation_count,
            theme_count=len(compile_manifest.themes),
            state_dir=str(self._settings.state_dir),
            compiled_dir=str(self._settings.compiled_dir),
            indexes_dir=str(self._settings.indexes_dir),
        )

    def inspect_chunk(self, chunk_id: str) -> ChunkInspection:
        for chunk in self.load_chunks():
            if chunk.chunk_id == chunk_id:
                return ChunkInspection(chunk=chunk)
        raise KeyError(f"Unknown chunk id: {chunk_id}")

    def inspect_topic(self, topic_id: str) -> TopicInspection:
        topics = {topic.topic_id: topic for topic in self.load_topics()}
        topic = topics.get(topic_id)
        if topic is None:
            raise KeyError(f"Unknown topic id: {topic_id}")

        claims = tuple(
            claim
            for claim in self.load_claims()
            if claim.claim_id.startswith(f"{topic_id}-claim-")
        )
        relations = tuple(
            relation
            for relation in self.load_relations()
            if relation.relation_id.startswith(f"{topic_id}-relation-")
        )
        return TopicInspection(topic=topic, claims=claims, relations=relations)

    def trace_last_answer(self) -> AnswerTrace:
        answer = self.load_last_answer()
        chunks_by_id = {chunk.chunk_id: chunk for chunk in self.load_chunks()}
        cited_chunks = tuple(
            chunks_by_id[citation.chunk_id]
            for citation in answer.citations
            if citation.chunk_id in chunks_by_id
        )
        return AnswerTrace(answer=answer, cited_chunks=cited_chunks)

    def persist_compile_bundle(
        self,
        *,
        topic_records: list[TopicRecord],
        markdown_artifacts: list[TopicMarkdownArtifact],
        claims: list[Claim],
        relations: list[Relation],
        manifest: CompileManifest,
    ) -> None:
        topics_dir = self._settings.compiled_dir / "topics"
        topics_dir.mkdir(parents=True, exist_ok=True)

        for artifact in markdown_artifacts:
            (topics_dir / f"{artifact.topic_id}.md").write_text(artifact.markdown, encoding="utf-8")

        self._write_json(
            self._settings.compiled_dir / "topics.json",
            [topic.model_dump(mode="json") for topic in topic_records],
        )
        self._write_jsonl(self._settings.compiled_dir / "claims.jsonl", claims)
        self._write_jsonl(self._settings.compiled_dir / "relations.jsonl", relations)
        self._write_json(
            self._settings.compiled_dir / "compile-manifest.json",
            manifest.model_dump(mode="json"),
        )

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _write_jsonl(self, path: Path, rows: Sequence[BaseModel]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row.model_dump(mode="json"), sort_keys=True))
                handle.write("\n")

    def _read_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_jsonl[ModelT: BaseModel](self, path: Path, model_type: type[ModelT]) -> list[ModelT]:
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(model_type.model_validate(json.loads(line)))
        return rows
