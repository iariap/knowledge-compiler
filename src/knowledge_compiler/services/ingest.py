from pathlib import Path

from knowledge_compiler.connectors import LocalFilesConnector
from knowledge_compiler.schemas import IngestManifest
from knowledge_compiler.storage import WorkspaceStore


def ingest_local_files(*, input_path: Path, store: WorkspaceStore) -> IngestManifest:
    connector = LocalFilesConnector(input_path)
    source = connector.describe_source()
    documents, chunks = connector.ingest()
    return store.persist_ingest_bundle(
        source=source,
        documents=documents,
        chunks=chunks,
    )
