import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from knowledge_compiler.ingestion.html_text import html_to_plain_text

from knowledge_compiler.cli import app
from knowledge_compiler.connectors import LocalFilesConnector


def test_local_connector_discovers_documents() -> None:
    connector = LocalFilesConnector(Path("tests/fixtures/input"))

    documents, chunks = connector.ingest()

    assert len(documents) == 2
    assert len(chunks) >= 2
    assert all(chunk.provenance.relative_path for chunk in chunks)


def test_ingest_command_writes_artifacts() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"
        result = runner.invoke(app, ["ingest", str(fixture_root.resolve())])

        assert result.exit_code == 0

        state_dir = Path("workspace/state")
        assert (state_dir / "sources.json").exists()
        assert (state_dir / "documents.jsonl").exists()
        assert (state_dir / "chunks.jsonl").exists()
        assert (state_dir / "ingest-manifest.json").exists()

        manifest = json.loads((state_dir / "ingest-manifest.json").read_text(encoding="utf-8"))
        assert manifest["document_count"] == 2
        assert manifest["chunk_count"] >= 2


def test_compile_command_writes_compiled_artifacts() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        ingest_result = runner.invoke(app, ["ingest", str(fixture_root.resolve())])
        assert ingest_result.exit_code == 0

        compile_result = runner.invoke(app, ["compile"])
        assert compile_result.exit_code == 0

        compiled_dir = Path("workspace/compiled")
        assert (compiled_dir / "topics.json").exists()
        assert (compiled_dir / "claims.jsonl").exists()
        assert (compiled_dir / "relations.jsonl").exists()
        assert (compiled_dir / "compile-manifest.json").exists()

        manifest = json.loads((compiled_dir / "compile-manifest.json").read_text(encoding="utf-8"))
        assert manifest["topic_count"] == 2
        assert manifest["claim_count"] >= 2
        assert manifest["relation_count"] >= 2
        assert manifest.get("theme_clustering") == "lexical-jaccard-v1"
        assert isinstance(manifest.get("themes", []), list)
        assert len(manifest["themes"]) >= 1

        topics = json.loads((compiled_dir / "topics.json").read_text(encoding="utf-8"))
        assert len(topics) == 2
        for row in topics:
            assert "theme_id" in row
            assert "theme_label" in row


def test_index_and_ask_commands_work_end_to_end() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0

        index_result = runner.invoke(app, ["index"])
        assert index_result.exit_code == 0
        assert Path("workspace/indexes/retrieval.db").exists()

        ask_result = runner.invoke(app, ["ask", "deterministic chunking"])
        assert ask_result.exit_code == 0
        assert "Deterministic chunking keeps citations stable" in ask_result.output
        assert "Citations:" in ask_result.output
        assert Path("workspace/state/last-evidence-pack.json").exists()


def test_inspect_workspace_chunk_and_topic_commands() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0

        workspace_result = runner.invoke(app, ["inspect", "workspace"])
        assert workspace_result.exit_code == 0
        assert "Documents: 2, chunks: 2, topics: 2" in workspace_result.output

        chunk_id = json.loads(Path("workspace/state/chunks.jsonl").read_text(encoding="utf-8").splitlines()[0])["chunk_id"]
        chunk_result = runner.invoke(app, ["inspect", "chunk", chunk_id])
        assert chunk_result.exit_code == 0
        assert "Source:" in chunk_result.output

        topic_id = json.loads(Path("workspace/compiled/topics.json").read_text(encoding="utf-8"))[0]["topic_id"]
        topic_result = runner.invoke(app, ["inspect", "topic", topic_id])
        assert topic_result.exit_code == 0
        assert "Supporting chunks:" in topic_result.output


def test_trace_command_traces_historical_ask_run() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0
        assert runner.invoke(app, ["ask", "deterministic chunking"]).exit_code == 0

        runs_out = runner.invoke(app, ["runs", "--limit", "5"])
        assert runs_out.exit_code == 0
        first_line = runs_out.output.strip().splitlines()[0]
        run_id = first_line.split(" | ", 1)[0]

        trace_result = runner.invoke(app, ["trace", "--run", run_id])
        assert trace_result.exit_code == 0
        assert "Query: deterministic chunking" in trace_result.output
        assert "Evidence:" in trace_result.output


def test_trace_command_uses_last_answer() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0
        assert runner.invoke(app, ["ask", "deterministic chunking"]).exit_code == 0

        trace_result = runner.invoke(app, ["trace"])
        assert trace_result.exit_code == 0
        assert "Query: deterministic chunking" in trace_result.output
        assert "Evidence:" in trace_result.output


def test_retrieve_command_writes_explicit_evidence_pack() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        retrieve_result = runner.invoke(app, ["retrieve", "deterministic chunking", "--limit", "3"])
        assert retrieve_result.exit_code == 0
        assert "Query: deterministic chunking" in retrieve_result.output
        assert "Evidence hits:" in retrieve_result.output

        evidence_pack = json.loads(Path("workspace/state/last-evidence-pack.json").read_text(encoding="utf-8"))
        assert evidence_pack["query"] == "deterministic chunking"
        assert len(evidence_pack["chunk_ids"]) >= 1
        assert len(evidence_pack["hits"]) >= 1


def test_retrieve_command_handles_natural_language_query_without_crashing() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        retrieve_result = runner.invoke(app, ["retrieve", "What did I write about API design?"])
        assert retrieve_result.exit_code == 0
        assert "Query: What did I write about API design?" in retrieve_result.output


def test_context_command_writes_bounded_context_pack() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        context_result = runner.invoke(
            app,
            ["context", "deterministic chunking", "--limit", "3", "--max-chars", "80"],
        )
        assert context_result.exit_code == 0
        assert "Context budget:" in context_result.output
        assert "Context snippets:" in context_result.output

        context_pack = json.loads(Path("workspace/state/last-context-pack.json").read_text(encoding="utf-8"))
        assert context_pack["query"] == "deterministic chunking"
        assert context_pack["selection_strategy"] == "query-aware-multi-snippet-v2"
        assert context_pack.get("estimated_input_tokens", 0) >= 1
        assert context_pack["used_chars"] <= 80
        assert len(context_pack["snippets"]) >= 1
        assert context_pack["snippets"][0]["matched_terms"] >= 1
        assert "Deterministic chunking keeps citations stable" in context_pack["snippets"][0]["text"]


def test_runs_command_lists_recent_query_history() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_root = Path(__file__).parent / "fixtures" / "input"

        assert runner.invoke(app, ["ingest", str(fixture_root.resolve())]).exit_code == 0
        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0
        assert runner.invoke(app, ["retrieve", "deterministic chunking"]).exit_code == 0
        assert runner.invoke(app, ["context", "deterministic chunking"]).exit_code == 0
        assert runner.invoke(app, ["ask", "deterministic chunking"]).exit_code == 0

        runs_result = runner.invoke(app, ["runs", "--limit", "5"])
        assert runs_result.exit_code == 0
        assert "retrieve |" in runs_result.output and "query='deterministic chunking'" in runs_result.output
        assert "context | query='deterministic chunking'" in runs_result.output
        assert "ask | query='deterministic chunking'" in runs_result.output

        run_lines = Path("workspace/state/query-runs.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(run_lines) >= 3


def test_html_to_plain_text_skips_script_and_keeps_body() -> None:
    html = "<html><body><p>Hello</p><script>evil()</script><p>World</p></body></html>"
    text = html_to_plain_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "evil" not in text


def test_merge_ingest_accumulates_two_sources() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_a = Path(__file__).resolve().parent / "fixtures" / "input"
        fixture_b = Path(__file__).resolve().parent / "fixtures" / "merge_b"
        Path("a").mkdir()
        Path("b").mkdir()
        shutil.copytree(fixture_a, Path("a"), dirs_exist_ok=True)
        shutil.copytree(fixture_b, Path("b"), dirs_exist_ok=True)

        assert runner.invoke(app, ["ingest", "a"]).exit_code == 0
        assert runner.invoke(app, ["ingest", "b", "--merge"]).exit_code == 0

        manifest = json.loads(Path("workspace/state/ingest-manifest.json").read_text(encoding="utf-8"))
        assert manifest["document_count"] == 4
        assert len(manifest["source_ids"]) == 2

        sources = json.loads(Path("workspace/state/sources.json").read_text(encoding="utf-8"))
        assert len(sources) == 2

        assert runner.invoke(app, ["compile"]).exit_code == 0
        assert runner.invoke(app, ["index"]).exit_code == 0

        inspect_out = runner.invoke(app, ["inspect", "workspace"])
        assert inspect_out.exit_code == 0
        assert "Sources (2):" in inspect_out.output

        compiled = json.loads(Path("workspace/compiled/compile-manifest.json").read_text(encoding="utf-8"))
        assert compiled["topic_count"] == 4
        assert compiled["source_id"] == "multi-source"
        assert len(compiled["source_ids"]) == 2

        retrieve = runner.invoke(app, ["retrieve", "Phoenix ledger", "--limit", "2"])
        assert retrieve.exit_code == 0
        assert "Phoenix" in retrieve.output

        html_retrieve = runner.invoke(app, ["retrieve", "Visible HTML paragraph", "--limit", "2"])
        assert html_retrieve.exit_code == 0
        assert "Visible" in html_retrieve.output or "ingestion" in html_retrieve.output


def test_second_ingest_without_merge_replaces_workspace() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        fixture_a = Path(__file__).resolve().parent / "fixtures" / "input"
        fixture_b = Path(__file__).resolve().parent / "fixtures" / "merge_b"
        Path("a").mkdir()
        Path("b").mkdir()
        shutil.copytree(fixture_a, Path("a"), dirs_exist_ok=True)
        shutil.copytree(fixture_b, Path("b"), dirs_exist_ok=True)

        assert runner.invoke(app, ["ingest", "a"]).exit_code == 0
        assert runner.invoke(app, ["ingest", "b"]).exit_code == 0

        manifest = json.loads(Path("workspace/state/ingest-manifest.json").read_text(encoding="utf-8"))
        assert manifest["document_count"] == 2
        assert len(manifest["source_ids"]) == 1
