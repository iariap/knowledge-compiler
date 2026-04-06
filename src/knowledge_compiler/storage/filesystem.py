import json
from pathlib import Path
from typing import Any

from knowledge_compiler.config import Settings
from knowledge_compiler.schemas import Chunk, Document, Source


def ensure_workspace(settings: Settings) -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    settings.compiled_dir.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def persist_ingest_artifacts(
    *,
    settings: Settings,
    source: Source,
    documents: list[Document],
    chunks: list[Chunk],
) -> None:
    write_json(settings.state_dir / "sources.json", [source.model_dump(mode="json")])
    write_jsonl(
        settings.state_dir / "documents.jsonl",
        [document.model_dump(mode="json") for document in documents],
    )
    write_jsonl(
        settings.state_dir / "chunks.jsonl",
        [chunk.model_dump(mode="json") for chunk in chunks],
    )
    write_json(
        settings.state_dir / "ingest-manifest.json",
        {
            "chunk_count": len(chunks),
            "document_count": len(documents),
            "source_id": source.source_id,
            "source_ids": [source.source_id],
        },
    )
