from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class QueryRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    command: str
    query: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int
    chunk_count: int
    topic_count: int = 0
    claim_count: int = 0
    context_chars: int | None = None
    answer_preview: str | None = None
    answer_text: str | None = None
    citation_chunk_ids: tuple[str, ...] = ()
