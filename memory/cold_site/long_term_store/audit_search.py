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



def _metadata_user_id(metadata: dict[str, object]) -> str | None:
    value = metadata.get("user_id")
    if value is None:
        return None
    return str(value)


def _event_in_scope(
    event: ArchivedEvent,
    *,
    project_id: str | None,
    user_id: str | None,
) -> bool:
    if project_id is not None and event.project_id != project_id:
        return False
    if user_id is not None and _metadata_user_id(dict(event.metadata)) != user_id:
        return False
    return True


class ColdHistorySearchService:
    """Perform explicit audit searches over the cold archive."""

    def __init__(
        self,
        archive: ColdEventArchive,
    ) -> None:
        self._archive = archive

    def _search(
        self,
        query: str,
        *,
        limit: int,
        project_id: str | None,
        user_id: str | None,
        source: RetrievalSource,
        audit_only: bool,
        exclude_event_ids: frozenset[str] = frozenset(),
    ) -> RetrievalResult:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty.")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer.")
        if limit <= 0:
            raise ValueError("limit must be positive.")

        scored_events: list[tuple[float, ArchivedEvent]] = []
        for event in self._archive.list_events():
            if event.event_id in exclude_event_ids:
                continue
            if not _event_in_scope(
                event,
                project_id=project_id,
                user_id=user_id,
            ):
                continue
            score = _audit_score(query, event)
            if score > 0.0:
                scored_events.append((score, event))

        scored_events.sort(
            key=lambda item: (item[0], item[1].archived_at),
            reverse=True,
        )

        matches: list[RetrievedMemory] = []
        for score, event in scored_events[:limit]:
            metadata = {
                "retrieval_tier": (
                    "cold_audit" if audit_only else "cold_site"
                ),
                "trust_level": (
                    "historical_audit"
                    if audit_only
                    else "historical_unvalidated"
                ),
                "audit_only": audit_only,
                "validated": False,
                "active_memory": False,
                "fallback": not audit_only,
                "event_type": event.event_type,
                "source": event.source,
                "original_created_at": event.original_created_at,
                "archived_at": event.archived_at,
                "project_id": event.project_id,
                "session_id": event.session_id,
                "user_id": _metadata_user_id(dict(event.metadata)),
                "archive_metadata": dict(event.metadata),
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
            source=source,
            matches=tuple(matches),
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> RetrievalResult:
        """Explicitly search durable history for audit purposes."""

        return self._search(
            query,
            limit=limit,
            project_id=project_id,
            user_id=user_id,
            source=RetrievalSource.COLD_AUDIT,
            audit_only=True,
        )

    def search_for_retrieval(
        self,
        query: str,
        *,
        limit: int = 10,
        project_id: str | None = None,
        user_id: str | None = None,
        exclude_event_ids: frozenset[str] = frozenset(),
    ) -> RetrievalResult:
        """Search durable history as the final normal-retrieval fallback."""

        return self._search(
            query,
            limit=limit,
            project_id=project_id,
            user_id=user_id,
            source=RetrievalSource.COLD_SITE,
            audit_only=False,
            exclude_event_ids=exclude_event_ids,
        )
