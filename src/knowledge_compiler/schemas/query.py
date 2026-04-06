from pydantic import BaseModel, ConfigDict


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    relative_path: str
    score: float
    text: str
    start_line: int
    end_line: int


class AnswerCitation(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    relative_path: str
    start_line: int
    end_line: int


class QueryAnswer(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    answer_text: str
    citations: tuple[AnswerCitation, ...]
    evidence: tuple[SearchHit, ...]
