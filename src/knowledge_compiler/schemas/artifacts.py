from pydantic import BaseModel, ConfigDict


class TopicRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic_id: str
    title: str
    summary: str
    supporting_chunk_ids: tuple[str, ...]
    document_id: str
    theme_id: str = ""
    theme_label: str = ""


class TopicMarkdownArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic_id: str
    markdown: str
