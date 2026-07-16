"""Filesystem paths used by the memoriX Python runtime.

Runtime data must remain outside the source repository by default.
Tests and callers may always inject an explicit temporary runtime root.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


MEMORY_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def resolve_default_runtime_root() -> Path:
    """Return a platform-appropriate runtime directory outside the repository."""

    explicit_root = os.environ.get("MEMORIX_RUNTIME_ROOT", "").strip()

    if explicit_root:
        return Path(explicit_root).expanduser().resolve()

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()

    if local_app_data:
        return (
            Path(local_app_data)
            / "memoriX"
            / "runtime"
        ).expanduser().resolve()

    xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()

    if xdg_data_home:
        return (
            Path(xdg_data_home)
            / "memoriX"
            / "runtime"
        ).expanduser().resolve()

    try:
        home = Path.home()
    except RuntimeError:
        home = None

    if home is not None:
        return (
            home
            / ".local"
            / "share"
            / "memoriX"
            / "runtime"
        ).resolve()

    return (
        Path(tempfile.gettempdir())
        / "memoriX"
        / "runtime"
    ).resolve()


DEFAULT_RUNTIME_ROOT = resolve_default_runtime_root()


@dataclass(frozen=True, slots=True)
class MemoryStoragePaths:
    """Resolved paths for all current memoriX storage components."""

    runtime_root: Path
    short_term_events: Path
    cold_archive_events: Path
    memory_candidates: Path
    titan_neural_state: Path
    titan_metadata: Path
    nightly_logs: Path
    project_archive_entries: Path
    project_archive_snapshots: Path

    @classmethod
    def from_runtime_root(
        cls,
        runtime_root: str | Path,
    ) -> "MemoryStoragePaths":
        """Build all runtime paths from one explicit root directory."""

        root = Path(runtime_root).expanduser().resolve()

        return cls(
            runtime_root=root,
            short_term_events=(
                root
                / "short_term"
                / "events.jsonl"
            ),
            cold_archive_events=(
                root
                / "cold_site"
                / "events_archive.jsonl"
            ),
            memory_candidates=(
                root
                / "candidates"
                / "memory_candidates.jsonl"
            ),
            titan_neural_state=(
                root
                / "hot_site"
                / "titan_memory.pt"
            ),
            titan_metadata=(
                root
                / "hot_site"
                / "titan_metadata.jsonl"
            ),
            nightly_logs=(
                root
                / "logs"
                / "nightly_consolidation.jsonl"
            ),
            project_archive_entries=(
                root
                / "cold_site"
                / "project_archive"
                / "project_entries.jsonl"
            ),
            project_archive_snapshots=(
                root
                / "cold_site"
                / "project_archive"
                / "project_snapshots.jsonl"
            ),
        )


DEFAULT_STORAGE_PATHS = MemoryStoragePaths.from_runtime_root(
    DEFAULT_RUNTIME_ROOT
)