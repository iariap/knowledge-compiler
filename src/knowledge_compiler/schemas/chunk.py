from pydantic import BaseModel, ConfigDict


class ChunkProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    document_id: str
    relative_path: str
    start_line: int
    end_line: int


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    ordinal: int
    text: str
    text_hash: str
    provenance: ChunkProvenance
