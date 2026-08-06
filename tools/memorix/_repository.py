"""Shared path helpers for memoriX command-line tools."""

from __future__ import annotations

from pathlib import Path


def find_repository_root(start: Path) -> Path:
    """Find the memoriX repository root from a tool path.

    The lookup is marker-based so command-line tools keep working when they
    are executed from any current working directory.
    """

    resolved = start.resolve()
    current = resolved.parent if resolved.is_file() else resolved

    for candidate in (current, *current.parents):
        if (
            (candidate / "package.json").is_file()
            and (candidate / "memory").is_dir()
            and (candidate / "packages" / "opencode").is_dir()
        ):
            return candidate

    raise RuntimeError(
        "Unable to locate the memoriX repository root from "
        f"{resolved}."
    )
