"""Safety guards for destructive runtime operations."""
from __future__ import annotations
import os
from pathlib import Path


def validate_destructive_runtime_path(path: str | Path, *, project_root: str | Path | None = None) -> Path:
    target = Path(path).expanduser().resolve()
    forbidden = {Path(target.anchor).resolve(), Path.home().resolve()}
    if os.environ.get("USERPROFILE"):
        forbidden.add(Path(os.environ["USERPROFILE"]).expanduser().resolve())
    if project_root is not None:
        project = Path(project_root).expanduser().resolve()
        forbidden.update({project, project / "memory", project / "memory" / "runtime"})
        try:
            target.relative_to(project)
        except ValueError:
            pass
        else:
            raise ValueError("Destructive runtime operations must target a directory outside the source repository.")
    if target in forbidden or len(target.parts) < 3:
        raise ValueError(f"Unsafe destructive runtime path: {target}")
    if target.name in {"", ".", "..", "memory", "src", "source", "repo", "repository"}:
        raise ValueError(f"Runtime path is too broad for destructive use: {target}")
    return target
