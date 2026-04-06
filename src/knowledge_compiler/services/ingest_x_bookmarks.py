from knowledge_compiler.connectors.x_bookmarks import XApiClient, XBookmarksConnector
from knowledge_compiler.schemas import IngestManifest
from knowledge_compiler.storage import WorkspaceStore


def ingest_x_bookmarks(
    *,
    store: WorkspaceStore,
    client: XApiClient | None = None,
    max_pages: int | None = None,
    page_size: int = 100,
    merge: bool = False,
) -> IngestManifest:
    resolved = client if client is not None else XApiClient.from_environment()
    connector = XBookmarksConnector(resolved, max_pages=max_pages, page_size=page_size)
    source = connector.describe_source()
    documents, chunks = connector.ingest()
    return store.persist_ingest_bundle(
        source=source,
        documents=documents,
        chunks=chunks,
        merge=merge,
    )
