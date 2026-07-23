"""Explicit candidate proposal service."""

from __future__ import annotations

from collections.abc import Iterable

from memory.consolidation.candidate_store import (
    MemoryCandidateStore,
)
from memory.data import (
    JSONValue,
    MemoryCandidate,
    Metadata,
)


class MemoryCandidateService:
    """Create pending candidates without validating them."""

    def __init__(
        self,
        candidate_store: MemoryCandidateStore,
    ) -> None:
        self._candidate_store = candidate_store

    def propose(
        self,
        *,
        content: str,
        reason: str,
        source_event_ids: Iterable[str],
        importance: float = 0.5,
        confidence: float = 0.5,
        surprise: float = 0.0,
        target_memory_id: str | None = None,
        metadata: Metadata | None = None,
    ) -> MemoryCandidate:
        """Create and persist one pending memory candidate."""

        candidate = MemoryCandidate(
            content=content,
            reason=reason,
            source_event_ids=tuple(source_event_ids),
            importance=importance,
            confidence=confidence,
            surprise=surprise,
            target_memory_id=target_memory_id,
            metadata=dict(metadata or {}),
        )

        return self._candidate_store.add(candidate)
