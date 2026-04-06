from pydantic import BaseModel, ConfigDict


class IngestManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    document_count: int
    chunk_count: int


class TopicManifestEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic_id: str
    title: str
    document_id: str
    relative_output_path: str
    supporting_chunk_ids: tuple[str, ...]
    theme_id: str = ""


class TopicThemeEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    theme_id: str
    label: str
    topic_ids: tuple[str, ...]


class CompileManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    topic_count: int
    claim_count: int
    relation_count: int
    topics: tuple[TopicManifestEntry, ...]
    themes: tuple[TopicThemeEntry, ...] = ()
    theme_clustering: str = "lexical-jaccard-v1"
