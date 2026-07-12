"""Typed domain contracts shared by the memoriX Python components.

This module contains data only. It does not perform storage, retrieval,
consolidation, Titan inference, MCP communication, or OpenCode integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, TypeAlias
from uuid import uuid4


JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = (
    JSONPrimitive
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)
Metadata: TypeAlias = dict[str, JSONValue]


def utc_now_iso() -> str:
    """Return the current UTC timestamp in an ISO-8601 representation."""

    return datetime.now(timezone.utc).isoformat()


def new_identifier(prefix: str) -> str:
    """Create a stable, human-readable identifier with a typed prefix."""

    normalized_prefix = prefix.strip().lower().replace(" ", "_")

    if not normalized_prefix:
        raise ValueError("Identifier prefix must not be empty.")

    return f"{normalized_prefix}_{uuid4().hex}"


def validate_iso_timestamp(value: str, field_name: str) -> None:
    """Validate that a string contains a timezone-aware ISO timestamp."""

    require_non_empty(value, field_name)

    normalized = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError(
            f"{field_name} must be a valid ISO-8601 timestamp."
        ) from error

    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information.")


def require_non_empty(value: str, field_name: str) -> None:
    """Reject empty or whitespace-only textual fields."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty.")


def validate_unit_score(value: float, field_name: str) -> None:
    """Ensure that a score is included in the closed interval [0, 1]."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number.")

    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def copy_metadata(
    value: Mapping[str, JSONValue] | None,
) -> Metadata:
    """Return a detached dictionary suitable for a domain model."""

    if value is None:
        return {}

    return dict(value)


class CandidateStatus(str, Enum):
    """Lifecycle states of a memory candidate."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class RetrievalSource(str, Enum):
    """Allowed retrieval sources under the active hot/cold contract."""

    HOT_SITE = "hot_site"
    COLD_AUDIT = "cold_audit"


class ForgetAction(str, Enum):
    """Possible hot-site forgetting outcomes."""

    WEAKENED = "weakened"
    DEACTIVATED = "deactivated"
    NOT_FOUND = "not_found"


@dataclass(slots=True)
class ShortTermEvent:
    """Recent event accepted by the memoriX gateway."""

    content: str
    event_type: str
    source: str
    event_id: str = field(
        default_factory=lambda: new_identifier("event")
    )
    created_at: str = field(default_factory=utc_now_iso)
    project_id: str | None = None
    session_id: str | None = None
    importance: float = 0.5
    confidence: float = 1.0
    surprise: float = 0.0
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.event_id, "event_id")
        require_non_empty(self.content, "content")
        require_non_empty(self.event_type, "event_type")
        require_non_empty(self.source, "source")
        validate_iso_timestamp(self.created_at, "created_at")
        validate_unit_score(self.importance, "importance")
        validate_unit_score(self.confidence, "confidence")
        validate_unit_score(self.surprise, "surprise")
        self.metadata = copy_metadata(self.metadata)

        if self.project_id is not None:
            require_non_empty(self.project_id, "project_id")

        if self.session_id is not None:
            require_non_empty(self.session_id, "session_id")

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the event to a JSON-compatible dictionary."""

        return {
            "event_id": self.event_id,
            "content": self.content,
            "event_type": self.event_type,
            "source": self.source,
            "created_at": self.created_at,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "importance": float(self.importance),
            "confidence": float(self.confidence),
            "surprise": float(self.surprise),
            "metadata": copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "ShortTermEvent":
        """Restore a short-term event from serialized data."""

        return cls(
            event_id=str(payload["event_id"]),
            content=str(payload["content"]),
            event_type=str(payload["event_type"]),
            source=str(payload["source"]),
            created_at=str(payload["created_at"]),
            project_id=(
                str(payload["project_id"])
                if payload.get("project_id") is not None
                else None
            ),
            session_id=(
                str(payload["session_id"])
                if payload.get("session_id") is not None
                else None
            ),
            importance=float(payload.get("importance", 0.5)),
            confidence=float(payload.get("confidence", 1.0)),
            surprise=float(payload.get("surprise", 0.0)),
            metadata=copy_metadata(payload.get("metadata")),
        )


@dataclass(slots=True)
class ArchivedEvent:
    """Durable cold-site representation of a short-term event."""

    event_id: str
    content: str
    event_type: str
    source: str
    original_created_at: str
    archived_at: str = field(default_factory=utc_now_iso)
    project_id: str | None = None
    session_id: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.event_id, "event_id")
        require_non_empty(self.content, "content")
        require_non_empty(self.event_type, "event_type")
        require_non_empty(self.source, "source")
        validate_iso_timestamp(
            self.original_created_at,
            "original_created_at",
        )
        validate_iso_timestamp(self.archived_at, "archived_at")
        self.metadata = copy_metadata(self.metadata)

        if self.project_id is not None:
            require_non_empty(self.project_id, "project_id")

        if self.session_id is not None:
            require_non_empty(self.session_id, "session_id")

    @classmethod
    def from_short_term_event(
        cls,
        event: ShortTermEvent,
        *,
        archived_at: str | None = None,
    ) -> "ArchivedEvent":
        """Create the durable historical form of a short-term event."""

        return cls(
            event_id=event.event_id,
            content=event.content,
            event_type=event.event_type,
            source=event.source,
            original_created_at=event.created_at,
            archived_at=archived_at or utc_now_iso(),
            project_id=event.project_id,
            session_id=event.session_id,
            metadata=copy_metadata(event.metadata),
        )

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the archived event."""

        return {
            "event_id": self.event_id,
            "content": self.content,
            "event_type": self.event_type,
            "source": self.source,
            "original_created_at": self.original_created_at,
            "archived_at": self.archived_at,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "metadata": copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "ArchivedEvent":
        """Restore an archived event from serialized data."""

        return cls(
            event_id=str(payload["event_id"]),
            content=str(payload["content"]),
            event_type=str(payload["event_type"]),
            source=str(payload["source"]),
            original_created_at=str(
                payload["original_created_at"]
            ),
            archived_at=str(payload["archived_at"]),
            project_id=(
                str(payload["project_id"])
                if payload.get("project_id") is not None
                else None
            ),
            session_id=(
                str(payload["session_id"])
                if payload.get("session_id") is not None
                else None
            ),
            metadata=copy_metadata(payload.get("metadata")),
        )


@dataclass(slots=True)
class MemoryCandidate:
    """Information proposed for human validation before hot-site storage."""

    content: str
    reason: str
    source_event_ids: tuple[str, ...]
    candidate_id: str = field(
        default_factory=lambda: new_identifier("candidate")
    )
    created_at: str = field(default_factory=utc_now_iso)
    status: CandidateStatus = CandidateStatus.PENDING
    importance: float = 0.5
    confidence: float = 0.5
    surprise: float = 0.0
    target_memory_id: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.candidate_id, "candidate_id")
        require_non_empty(self.content, "content")
        require_non_empty(self.reason, "reason")
        validate_iso_timestamp(self.created_at, "created_at")
        validate_unit_score(self.importance, "importance")
        validate_unit_score(self.confidence, "confidence")
        validate_unit_score(self.surprise, "surprise")
        self.status = CandidateStatus(self.status)
        self.source_event_ids = tuple(self.source_event_ids)
        self.metadata = copy_metadata(self.metadata)

        if not self.source_event_ids:
            raise ValueError(
                "source_event_ids must contain at least one event ID."
            )

        for event_id in self.source_event_ids:
            require_non_empty(event_id, "source_event_id")

        if self.target_memory_id is not None:
            require_non_empty(
                self.target_memory_id,
                "target_memory_id",
            )

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the candidate."""

        return {
            "candidate_id": self.candidate_id,
            "content": self.content,
            "reason": self.reason,
            "source_event_ids": list(self.source_event_ids),
            "created_at": self.created_at,
            "status": self.status.value,
            "importance": float(self.importance),
            "confidence": float(self.confidence),
            "surprise": float(self.surprise),
            "target_memory_id": self.target_memory_id,
            "metadata": copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "MemoryCandidate":
        """Restore a memory candidate from serialized data."""

        return cls(
            candidate_id=str(payload["candidate_id"]),
            content=str(payload["content"]),
            reason=str(payload["reason"]),
            source_event_ids=tuple(
                str(value)
                for value in payload["source_event_ids"]
            ),
            created_at=str(payload["created_at"]),
            status=CandidateStatus(
                payload.get("status", CandidateStatus.PENDING.value)
            ),
            importance=float(payload.get("importance", 0.5)),
            confidence=float(payload.get("confidence", 0.5)),
            surprise=float(payload.get("surprise", 0.0)),
            target_memory_id=(
                str(payload["target_memory_id"])
                if payload.get("target_memory_id") is not None
                else None
            ),
            metadata=copy_metadata(payload.get("metadata")),
        )


@dataclass(slots=True)
class ValidatedMemory:
    """Curated active memory accepted for storage in the hot site."""

    content: str
    source_candidate_id: str
    memory_id: str = field(
        default_factory=lambda: new_identifier("memory")
    )
    created_at: str = field(default_factory=utc_now_iso)
    validated_at: str = field(default_factory=utc_now_iso)
    active: bool = True
    version: int = 1
    supersedes_memory_id: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.memory_id, "memory_id")
        require_non_empty(self.content, "content")
        require_non_empty(
            self.source_candidate_id,
            "source_candidate_id",
        )
        validate_iso_timestamp(self.created_at, "created_at")
        validate_iso_timestamp(self.validated_at, "validated_at")

        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean.")

        if isinstance(self.version, bool) or not isinstance(
            self.version,
            int,
        ):
            raise TypeError("version must be an integer.")

        if self.version < 1:
            raise ValueError("version must be greater than or equal to 1.")

        if self.supersedes_memory_id is not None:
            require_non_empty(
                self.supersedes_memory_id,
                "supersedes_memory_id",
            )

        self.metadata = copy_metadata(self.metadata)

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the validated memory."""

        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "source_candidate_id": self.source_candidate_id,
            "created_at": self.created_at,
            "validated_at": self.validated_at,
            "active": self.active,
            "version": self.version,
            "supersedes_memory_id": self.supersedes_memory_id,
            "metadata": copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "ValidatedMemory":
        """Restore a validated memory from serialized data."""

        return cls(
            memory_id=str(payload["memory_id"]),
            content=str(payload["content"]),
            source_candidate_id=str(
                payload["source_candidate_id"]
            ),
            created_at=str(payload["created_at"]),
            validated_at=str(payload["validated_at"]),
            active=bool(payload.get("active", True)),
            version=int(payload.get("version", 1)),
            supersedes_memory_id=(
                str(payload["supersedes_memory_id"])
                if payload.get("supersedes_memory_id") is not None
                else None
            ),
            metadata=copy_metadata(payload.get("metadata")),
        )


@dataclass(slots=True)
class RetrievedMemory:
    """One scored memory returned by an active-memory search."""

    memory_id: str
    content: str
    score: float
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty(self.memory_id, "memory_id")
        require_non_empty(self.content, "content")
        validate_unit_score(self.score, "score")
        self.metadata = copy_metadata(self.metadata)

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize one retrieval match."""

        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "score": float(self.score),
            "metadata": copy_metadata(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "RetrievedMemory":
        """Restore a retrieval match."""

        return cls(
            memory_id=str(payload["memory_id"]),
            content=str(payload["content"]),
            score=float(payload["score"]),
            metadata=copy_metadata(payload.get("metadata")),
        )


@dataclass(slots=True)
class RetrievalResult:
    """Result envelope for hot-site or explicit cold-audit searches."""

    query: str
    source: RetrievalSource
    matches: tuple[RetrievedMemory, ...] = ()
    retrieved_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        require_non_empty(self.query, "query")
        validate_iso_timestamp(self.retrieved_at, "retrieved_at")
        self.source = RetrievalSource(self.source)
        self.matches = tuple(self.matches)

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the retrieval result."""

        return {
            "query": self.query,
            "source": self.source.value,
            "retrieved_at": self.retrieved_at,
            "matches": [
                match.to_dict()
                for match in self.matches
            ],
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "RetrievalResult":
        """Restore a retrieval result."""

        return cls(
            query=str(payload["query"]),
            source=RetrievalSource(payload["source"]),
            retrieved_at=str(payload["retrieved_at"]),
            matches=tuple(
                RetrievedMemory.from_dict(match)
                for match in payload.get("matches", [])
            ),
        )


@dataclass(slots=True)
class ForgetResult:
    """Outcome of a hot-site-only soft-forget operation."""

    memory_id: str
    action: ForgetAction
    reason: str
    changed_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        require_non_empty(self.memory_id, "memory_id")
        require_non_empty(self.reason, "reason")
        validate_iso_timestamp(self.changed_at, "changed_at")
        self.action = ForgetAction(self.action)

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the soft-forget outcome."""

        return {
            "memory_id": self.memory_id,
            "action": self.action.value,
            "reason": self.reason,
            "changed_at": self.changed_at,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "ForgetResult":
        """Restore a soft-forget result."""

        return cls(
            memory_id=str(payload["memory_id"]),
            action=ForgetAction(payload["action"]),
            reason=str(payload["reason"]),
            changed_at=str(payload["changed_at"]),
        )
