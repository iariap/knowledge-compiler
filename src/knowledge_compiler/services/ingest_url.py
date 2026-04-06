from knowledge_compiler.connectors.url_fetch import describe_url_source, url_to_document_and_chunks
from knowledge_compiler.schemas import Chunk, Document, IngestManifest
from knowledge_compiler.storage import WorkspaceStore


def ingest_urls(*, urls: tuple[str, ...], store: WorkspaceStore, merge: bool = False) -> IngestManifest:
    source = describe_url_source()
    documents: list[Document] = []
    chunks: list[Chunk] = []
    for url in urls:
        doc, doc_chunks = url_to_document_and_chunks(url.strip())
        documents.append(doc)
        chunks.extend(doc_chunks)
    return store.persist_ingest_bundle(
        source=source,
        documents=documents,
        chunks=chunks,
        merge=merge,
    )
