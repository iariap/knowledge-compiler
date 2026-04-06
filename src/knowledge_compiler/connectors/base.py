from pathlib import Path
from typing import Protocol

from knowledge_compiler.schemas import Chunk, Document, Source


class Connector(Protocol):
    def describe_source(self) -> Source:
        """Return the source metadata handled by this connector."""

    def ingest(self) -> tuple[list[Document], list[Chunk]]:
        """Discover documents and normalize them into chunks."""


type SupportedPath = Path
