import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_root: Path
    workspace_dir: Path
    raw_dir: Path
    state_dir: Path
    compiled_dir: Path
    indexes_dir: Path

    @classmethod
    def from_project_root(cls, project_root: Path | None = None) -> "Settings":
        """Resolve project root: explicit path, else ``KNOWLEDGE_COMPILER_ROOT``, else cwd."""
        if project_root is not None:
            root = project_root.resolve()
        else:
            env_root = os.environ.get("KNOWLEDGE_COMPILER_ROOT", "").strip()
            root = Path(env_root).resolve() if env_root else Path.cwd().resolve()
        workspace_dir = root / "workspace"
        return cls(
            project_root=root,
            workspace_dir=workspace_dir,
            raw_dir=workspace_dir / "raw",
            state_dir=workspace_dir / "state",
            compiled_dir=workspace_dir / "compiled",
            indexes_dir=workspace_dir / "indexes",
        )
