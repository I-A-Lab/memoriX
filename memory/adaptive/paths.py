"""Derived paths for adaptive-memory state.

Part 12D keeps these paths separate from core storage contracts so that the
existing hot/cold layout and constructors remain unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AdaptiveStoragePaths:
    """Paths derived from the existing memoriX runtime root."""

    root: Path
    topic_blocks: Path
    routing_history: Path

    @classmethod
    def from_runtime_root(
        cls,
        runtime_root: Path | str,
    ) -> "AdaptiveStoragePaths":
        root = Path(runtime_root) / "adaptive"

        return cls(
            root=root,
            topic_blocks=(
                root / "topic_blocks.json"
            ),
            routing_history=(
                root / "routing_history.jsonl"
            ),
        )
