"""Explicit audit-only search over the durable cold-site event history.

This module is deliberately separate from active-memory retrieval. It never
writes to Titan and never rehydrates archived events into the hot site.
"""

from __future__ import annotations

import re

from memory.cold_site.long_term_store.event_archive import (
    ColdEventArchive,
)
from memory.data import (
    ArchivedEvent,
    RetrievalResult,
    RetrievalSource,
    RetrievedMemory,
)


def _tokens(value: str) -> set[str]:
    """Extract meaningful lowercase lexical tokens."""

    return {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9_'-]+",
            value.lower(),
        )
        if len(token) > 1
    }


def _audit_score(
    query: str,
    event: ArchivedEvent,
) -> float:
    """Return a bounded lexical audit-search score."""

    normalized_query = " ".join(query.lower().split())
    normalized_content = " ".join(
        event.content.lower().split()
    )

    query_tokens = _tokens(normalized_query)
    content_tokens = _tokens(normalized_content)

    if not query_tokens or not content_tokens:
        return 0.0

    intersection = query_tokens & content_tokens

    if not intersection:
        return 0.0

    query_coverage = len(intersection) / len(query_tokens)
    jaccard = len(intersection) / len(
        query_tokens | content_tokens
    )

    exact_phrase_bonus = (
        0.35
        if normalized_query in normalized_content
        else 0.0
    )

    score = (
        0.45 * query_coverage
        + 0.20 * jaccard
        + exact_phrase_bonus
    )

    return min(1.0, max(0.0, score))


class ColdHistorySearchService:
    """Perform explicit audit searches over the cold archive."""

    def __init__(
        self,
        archive: ColdEventArchive,
    ) -> None:
        self._archive = archive

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> RetrievalResult:
        """Search durable history without affecting active memory."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty.")

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer.")

        if limit <= 0:
            raise ValueError("limit must be positive.")

        scored_events: list[
            tuple[float, ArchivedEvent]
        ] = []

        for event in self._archive.list_events():
            score = _audit_score(query, event)

            if score > 0.0:
                scored_events.append((score, event))

        scored_events.sort(
            key=lambda item: (
                item[0],
                item[1].archived_at,
            ),
            reverse=True,
        )

        matches: list[RetrievedMemory] = []

        for score, event in scored_events[:limit]:
            metadata = {
                "audit_only": True,
                "active_memory": False,
                "event_type": event.event_type,
                "source": event.source,
                "original_created_at": (
                    event.original_created_at
                ),
                "archived_at": event.archived_at,
                "project_id": event.project_id,
                "session_id": event.session_id,
                "archive_metadata": dict(
                    event.metadata
                ),
                "cold_site_contract": (
                    "explicit_history_search_only"
                ),
                "automatic_rehydration": False,
            }

            matches.append(
                RetrievedMemory(
                    memory_id=event.event_id,
                    content=event.content,
                    score=score,
                    metadata=metadata,
                )
            )

        return RetrievalResult(
            query=query,
            source=RetrievalSource.COLD_AUDIT,
            matches=tuple(matches),
        )
