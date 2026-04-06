from knowledge_compiler.retrieval.sqlite_index import SqliteChunkIndex
from knowledge_compiler.storage import WorkspaceStore


def build_search_index(*, store: WorkspaceStore) -> int:
    chunks = store.load_chunks()
    index = SqliteChunkIndex(store.settings.indexes_dir / "retrieval.db")
    return index.rebuild(chunks)
