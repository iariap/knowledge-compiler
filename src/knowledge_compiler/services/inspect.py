from knowledge_compiler.schemas import ChunkInspection, TopicInspection, WorkspaceInspection
from knowledge_compiler.storage import WorkspaceStore


def inspect_workspace(*, store: WorkspaceStore) -> WorkspaceInspection:
    return store.inspect_workspace()


def inspect_chunk(*, chunk_id: str, store: WorkspaceStore) -> ChunkInspection:
    return store.inspect_chunk(chunk_id)


def inspect_topic(*, topic_id: str, store: WorkspaceStore) -> TopicInspection:
    return store.inspect_topic(topic_id)
