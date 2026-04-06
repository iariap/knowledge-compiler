"""Load a local ``.env`` file into ``os.environ`` (non-destructive: does not override existing vars)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_local_env(project_root: Path | None = None) -> None:
    """Load ``.env`` from project root, ``KNOWLEDGE_COMPILER_ROOT``, or cwd (first existing file)."""
    path = resolve_dotenv_path(project_root)
    if path.is_file():
        load_dotenv(path, override=False)


def resolve_dotenv_path(project_root: Path | None = None) -> Path:
    if project_root is not None:
        return project_root.resolve() / ".env"
    env_root = os.environ.get("KNOWLEDGE_COMPILER_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve() / ".env"
    return Path.cwd() / ".env"
