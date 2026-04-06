from pydantic import BaseModel, ConfigDict


class ContextSnippet(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    relative_path: str
    start_line: int
    end_line: int
    text: str
    score: float
    matched_terms: int


class ContextPack(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    source_hit_count: int
    selection_strategy: str
    max_chars: int
    used_chars: int
    estimated_input_tokens: int = 0
    max_tokens: int | None = None
    used_tokens: int = 0
    chunk_ids: tuple[str, ...]
    topic_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    snippets: tuple[ContextSnippet, ...]
