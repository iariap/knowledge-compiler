from pathlib import Path

from knowledge_compiler.connectors.base import Connector
from knowledge_compiler.ingestion.chunking import chunk_document
from knowledge_compiler.ingestion.discover import discover_files
from knowledge_compiler.ingestion.normalize import build_document
from knowledge_compiler.schemas import Chunk, Document, Source


class LocalFilesConnector(Connector):
    def __init__(self, root: Path, include_extensions: tuple[str, ...] = ("md", "txt")) -> None:
        self._root = root.resolve()
        self._include_extensions = include_extensions

    def describe_source(self) -> Source:
        return Source(
            source_id=f"local-files-{self._root.name or 'root'}",
            source_type="local_files",
            root_path=str(self._root),
            include_extensions=self._include_extensions,
        )

    def ingest(self) -> tuple[list[Document], list[Chunk]]:
        source = self.describe_source()
        documents: list[Document] = []
        chunks: list[Chunk] = []

        for path in discover_files(self._root, source.include_extensions):
            document, text = build_document(source_id=source.source_id, root=self._root, path=path)
            documents.append(document)
            chunks.extend(chunk_document(document, text))

        return documents, chunks
