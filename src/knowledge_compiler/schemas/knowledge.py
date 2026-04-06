from pydantic import BaseModel, ConfigDict

from knowledge_compiler.schemas.query import SearchHit


class TopicPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic_id: str
    title: str
    summary: str
    supporting_chunk_ids: tuple[str, ...] = ()


class Claim(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    text: str
    supporting_chunk_ids: tuple[str, ...]


class Relation(BaseModel):
    model_config = ConfigDict(frozen=True)

    relation_id: str
    subject: str
    predicate: str
    object: str
    supporting_claim_ids: tuple[str, ...] = ()


class EvidencePack(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    chunk_ids: tuple[str, ...]
    hits: tuple[SearchHit, ...]
    topic_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    match_mode: str = "and"
    ranking_strategy: str = "bm25_lexical_diversify"
    candidate_hits_fetched: int = 0
    max_chunks_per_document: int = 2
