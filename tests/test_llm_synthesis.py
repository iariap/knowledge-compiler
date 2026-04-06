import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from knowledge_compiler.cli import app
from knowledge_compiler.schemas import ContextPack, ContextSnippet
from knowledge_compiler.services.llm_synthesis import synthesize_answer_from_context


def test_synthesize_answer_from_context_parses_chat_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "sk-test")

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        payload = {"choices": [{"message": {"content": "  Grounded reply.  "}}]}
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    pack = ContextPack(
        query="q",
        source_hit_count=1,
        selection_strategy="test",
        max_chars=2000,
        used_chars=50,
        estimated_input_tokens=10,
        max_tokens=None,
        used_tokens=0,
        chunk_ids=("c1",),
        topic_ids=(),
        claim_ids=(),
        snippets=(
            ContextSnippet(
                chunk_id="c1",
                relative_path="a.md",
                start_line=1,
                end_line=2,
                text="Fact one about the topic.",
                score=1.0,
                matched_terms=1,
            ),
        ),
    )

    with patch("knowledge_compiler.services.llm_synthesis.urlopen", fake_urlopen):
        text = synthesize_answer_from_context(query="What is the topic?", context_pack=pack)

    assert text == "Grounded reply."


def test_ask_llm_end_to_end_with_mock_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_OPENAI_API_KEY", "sk-test")

    def fake_urlopen(request: object, timeout: object = None) -> io.BytesIO:
        payload = {"choices": [{"message": {"content": "LLM says: deterministic chunking matters."}}]}
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    runner = CliRunner()
    with runner.isolated_filesystem():
        fixture_root = Path(__file__).resolve().parent / "fixtures" / "input"
        assert runner.invoke(app, ["ingest", str(fixture_root)]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        with patch("knowledge_compiler.services.llm_synthesis.urlopen", fake_urlopen):
            result = runner.invoke(app, ["ask", "--llm", "deterministic chunking"])

        assert result.exit_code == 0
        assert "LLM says" in result.output
        assert "OpenAI-compatible chat" in result.output
