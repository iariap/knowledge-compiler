from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class IngestManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_count: int
    chunk_count: int
    source_id: str = ""
    source_ids: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def _coerce_ingest_sources(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        raw_ids = out.get("source_ids")
        sid = out.get("source_id") or ""
        if raw_ids in (None, (), []):
            if sid:
                out["source_ids"] = (sid,)
        else:
            out["source_ids"] = tuple(raw_ids) if not isinstance(raw_ids, tuple) else raw_ids
        ids: tuple[str, ...] = out.get("source_ids") or ()
        if not out.get("source_id") and ids:
            out["source_id"] = ids[0] if len(ids) == 1 else "multi-source"
        return out


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

    topic_count: int
    claim_count: int
    relation_count: int
    topics: tuple[TopicManifestEntry, ...]
    source_id: str = ""
    source_ids: tuple[str, ...] = ()
    themes: tuple[TopicThemeEntry, ...] = ()
    theme_clustering: str = "lexical-jaccard-v1"
    lexical_cross_topic_links: int = 0
    cross_topic_mode: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_compile_sources(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        raw_ids = out.get("source_ids")
        sid = out.get("source_id") or ""
        if raw_ids in (None, (), []):
            if sid:
                out["source_ids"] = (sid,)
        else:
            out["source_ids"] = tuple(raw_ids) if not isinstance(raw_ids, tuple) else raw_ids
        ids: tuple[str, ...] = out.get("source_ids") or ()
        if not out.get("source_id") and ids:
            out["source_id"] = ids[0] if len(ids) == 1 else "multi-source"
        return out
