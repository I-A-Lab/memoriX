"""Lexical fallback retrieval over recent short-term events."""

from __future__ import annotations

import re
from typing import Mapping, Any

from memory.data import (
    RetrievalResult,
    RetrievalSource,
    RetrievedMemory,
    ShortTermEvent,
)
from memory.hot_site.short_term_memory import ShortTermEventStore


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-zA-ZÀ-ÿ0-9_'-]+",
            value.lower(),
        )
        if len(token) > 1
    }


def lexical_score(query: str, content: str) -> float:
    """Return a bounded lexical fallback score."""

    normalized_query = " ".join(query.lower().split())
    normalized_content = " ".join(content.lower().split())

    query_tokens = _tokens(normalized_query)
    content_tokens = _tokens(normalized_content)

    if not query_tokens or not content_tokens:
        return 0.0

    intersection = query_tokens & content_tokens
    if not intersection:
        return 0.0

    query_coverage = len(intersection) / len(query_tokens)
    jaccard = len(intersection) / len(query_tokens | content_tokens)
    exact_phrase_bonus = (
        0.35 if normalized_query in normalized_content else 0.0
    )
    score = 0.45 * query_coverage + 0.20 * jaccard + exact_phrase_bonus
    return min(1.0, max(0.0, score))


def _metadata_user_id(metadata: Mapping[str, Any]) -> str | None:
    value = metadata.get("user_id")
    if value is None:
        return None
    return str(value)


def _event_in_scope(
    event: ShortTermEvent,
    *,
    project_id: str | None,
    user_id: str | None,
) -> bool:
    if project_id is not None and event.project_id != project_id:
        return False
    if user_id is not None and _metadata_user_id(event.metadata) != user_id:
        return False
    return True


class ShortTermSearchService:
    """Retrieve recent unvalidated events as a secondary fallback tier."""

    def __init__(self, store: ShortTermEventStore) -> None:
        self._store = store

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> RetrievalResult:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must not be empty.")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer.")
        if limit <= 0:
            raise ValueError("limit must be positive.")

        scored: list[tuple[float, ShortTermEvent]] = []
        for event in self._store.list_events():
            if not _event_in_scope(
                event,
                project_id=project_id,
                user_id=user_id,
            ):
                continue
            score = lexical_score(query, event.content)
            if score > 0.0:
                scored.append((score, event))

        scored.sort(
            key=lambda item: (item[0], item[1].created_at),
            reverse=True,
        )

        matches = []
        for score, event in scored[:limit]:
            matches.append(
                RetrievedMemory(
                    memory_id=event.event_id,
                    content=event.content,
                    score=score,
                    metadata={
                        "retrieval_tier": "short_term",
                        "trust_level": "recent_unvalidated",
                        "validated": False,
                        "active_memory": False,
                        "fallback": True,
                        "event_type": event.event_type,
                        "source": event.source,
                        "created_at": event.created_at,
                        "project_id": event.project_id,
                        "session_id": event.session_id,
                        "user_id": _metadata_user_id(event.metadata),
                        "event_metadata": dict(event.metadata),
                    },
                )
            )

        return RetrievalResult(
            query=query,
            source=RetrievalSource.SHORT_TERM,
            matches=tuple(matches),
        )
