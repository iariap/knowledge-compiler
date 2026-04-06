from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_type: str
    root_path: str
    include_extensions: tuple[str, ...]


class Document(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    source_id: str
    relative_path: str
    absolute_path: str
    title: str
    content_hash: str
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def path(self) -> Path:
        return Path(self.absolute_path)
