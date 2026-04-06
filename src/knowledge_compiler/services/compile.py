from knowledge_compiler.compile.pipeline import compile_knowledge
from knowledge_compiler.schemas import CompileManifest
from knowledge_compiler.storage import WorkspaceStore


def compile_workspace(*, store: WorkspaceStore) -> CompileManifest:
    documents = store.load_documents()
    chunks = store.load_chunks()

    topic_records, markdown_artifacts, claims, relations, manifest = compile_knowledge(
        documents=documents,
        chunks=chunks,
    )
    store.persist_compile_bundle(
        topic_records=topic_records,
        markdown_artifacts=markdown_artifacts,
        claims=claims,
        relations=relations,
        manifest=manifest,
    )
    return manifest
