import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from knowledge_compiler.cli import app


def test_merge_reingest_skips_unchanged_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        fixture = Path(__file__).resolve().parent / "fixtures" / "input"
        Path("corpus").mkdir()
        shutil.copytree(fixture, Path("corpus"), dirs_exist_ok=True)

        assert runner.invoke(app, ["ingest", "corpus"]).exit_code == 0
        first_chunks = Path("workspace/state/chunks.jsonl").read_text(encoding="utf-8")

        assert runner.invoke(app, ["ingest", "corpus", "--merge"]).exit_code == 0
        second_chunks = Path("workspace/state/chunks.jsonl").read_text(encoding="utf-8")

        assert first_chunks == second_chunks
