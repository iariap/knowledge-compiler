import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from knowledge_compiler.cli import app
from knowledge_compiler.retrieval.embedding_rerank import embedding_rerank_hits
from knowledge_compiler.schemas import SearchHit


def test_embedding_rerank_reorders_by_cosine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "sk-test")

    def fake_fetch(*, texts: list[str], api_key: str, base_url: str, model: str) -> list[list[float]]:
        _ = api_key, base_url, model
        out: list[list[float]] = []
        for t in texts:
            if t == "query":
                out.append([1.0, 0.0])
            elif "alpha" in t:
                out.append([0.9, 0.1])
            else:
                out.append([0.1, 0.9])
        return out

    hits = [
        SearchHit(
            chunk_id="b",
            document_id="d",
            relative_path="b.md",
            score=10.0,
            text="beta only",
            start_line=1,
            end_line=2,
        ),
        SearchHit(
            chunk_id="a",
            document_id="d",
            relative_path="a.md",
            score=1.0,
            text="alpha match",
            start_line=1,
            end_line=2,
        ),
    ]

    with patch(
        "knowledge_compiler.retrieval.embedding_rerank.fetch_embedding_vectors",
        fake_fetch,
    ):
        ranked = embedding_rerank_hits(hits, query="query", api_key="x", base_url="https://api.openai.com", model="m")

    assert ranked[0].chunk_id == "a"
    assert ranked[0].score >= ranked[1].score


def test_retrieve_embed_rerank_cli_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KNOWLEDGE_COMPILER_OPENAI_API_KEY", raising=False)
    runner = CliRunner()
    with runner.isolated_filesystem():
        fixture = Path(__file__).resolve().parent / "fixtures" / "input"
        assert runner.invoke(app, ["ingest", str(fixture)]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0
        result = runner.invoke(app, ["retrieve", "test", "--embed-rerank"])
        assert result.exit_code == 1
        assert "OPENAI_API_KEY" in result.output


def test_retrieve_embed_rerank_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "sk-test")

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        body = getattr(request, "data", b"{}")
        parsed = json.loads(body.decode("utf-8"))
        inputs = parsed.get("input") or []
        data = [{"index": i, "embedding": [1.0 / (i + 1), 0.0]} for i in range(len(inputs))]
        return io.BytesIO(json.dumps({"data": data}).encode("utf-8"))

    runner = CliRunner()
    with runner.isolated_filesystem():
        fixture = Path(__file__).resolve().parent / "fixtures" / "input"
        assert runner.invoke(app, ["ingest", str(fixture)]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        with patch("knowledge_compiler.retrieval.openai_embeddings.urlopen", fake_urlopen):
            result = runner.invoke(app, ["retrieve", "deterministic", "--embed-rerank", "--limit", "2"])

        assert result.exit_code == 0
        assert "openai_embed" in result.output
