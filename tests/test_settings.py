from pathlib import Path

from typer.testing import CliRunner

from knowledge_compiler.cli import app
from knowledge_compiler.config import Settings


def test_settings_uses_cwd_when_env_unset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("KNOWLEDGE_COMPILER_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_project_root()
    assert settings.project_root == tmp_path.resolve()


def test_settings_respects_knowledge_compiler_root(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "my-project"
    project.mkdir()
    monkeypatch.setenv("KNOWLEDGE_COMPILER_ROOT", str(project))
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_project_root()
    assert settings.project_root == project.resolve()
    assert settings.workspace_dir == project.resolve() / "workspace"


def test_cli_project_root_short_flag_writes_workspace_under_that_path(tmp_path: Path) -> None:
    runner = CliRunner()
    project = tmp_path / "repo"
    project.mkdir()
    fixture = Path(__file__).resolve().parent / "fixtures" / "input"
    result = runner.invoke(app, ["-p", str(project), "ingest", str(fixture)])
    assert result.exit_code == 0
    assert (project / "workspace" / "state" / "documents.jsonl").is_file()
