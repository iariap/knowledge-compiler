from pydantic import BaseModel, ConfigDict

from knowledge_compiler.schemas.artifacts import TopicRecord
from knowledge_compiler.schemas.chunk import Chunk
from knowledge_compiler.schemas.knowledge import Claim, Relation
from knowledge_compiler.schemas.manifests import CompileManifest, IngestManifest
from knowledge_compiler.schemas.query import QueryAnswer


class WorkspaceInspection(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    document_count: int
    chunk_count: int
    topic_count: int
    claim_count: int
    relation_count: int
    theme_count: int = 0
    state_dir: str
    compiled_dir: str
    indexes_dir: str


class ChunkInspection(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: Chunk


class TopicInspection(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: TopicRecord
    claims: tuple[Claim, ...]
    relations: tuple[Relation, ...]


class AnswerTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: QueryAnswer
    cited_chunks: tuple[Chunk, ...]
