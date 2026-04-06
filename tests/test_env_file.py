import os
from pathlib import Path

import pytest

from knowledge_compiler.env_file import load_local_env, resolve_dotenv_path


def test_resolve_dotenv_path_prefers_explicit_project_root(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    assert resolve_dotenv_path(project) == project.resolve() / ".env"


def test_load_local_env_loads_file_without_overriding_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "KNOWLEDGE_COMPILER_X_ACCESS_TOKEN=from-dotenv\n",
        encoding="utf-8",
    )
    load_local_env(None)
    assert os.environ.get("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN") == "from-dotenv"


def test_load_local_env_does_not_override_shell_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN", "from-shell")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "KNOWLEDGE_COMPILER_X_ACCESS_TOKEN=from-dotenv\n",
        encoding="utf-8",
    )
    load_local_env(None)
    assert os.environ.get("KNOWLEDGE_COMPILER_X_ACCESS_TOKEN") == "from-shell"
