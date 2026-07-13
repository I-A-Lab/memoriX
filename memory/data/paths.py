"""Filesystem paths used by the memoriX Python runtime.

The defaults are intentionally centralized here so storage components do not
construct their own unrelated paths. Tests may inject temporary paths and must
not write into the project runtime directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


MEMORY_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = MEMORY_PACKAGE_ROOT / "runtime"


@dataclass(frozen=True, slots=True)
class MemoryStoragePaths:
    """Resolved paths for short-term, cold-site, and hot-site storage."""

    runtime_root: Path
    short_term_events: Path
    cold_archive_events: Path
    titan_neural_state: Path
    titan_metadata: Path

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
        )


DEFAULT_STORAGE_PATHS = MemoryStoragePaths.from_runtime_root(
    DEFAULT_RUNTIME_ROOT
)
