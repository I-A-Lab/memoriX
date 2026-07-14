"""Shared contracts for observable adaptive-memory metrics.

These contracts are deliberately action-free. They describe observations
only and must not trigger expansion, pruning, validation, or rehydration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class PressureLevel(str, Enum):
    """Human-readable interpretation of an observed pressure score."""

    STABLE = "stable"
    WATCH = "watch"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class PressureWeights:
    """Weights used to combine normalized pressure components."""

    usage_ratio: float = 0.40
    momentum: float = 0.20
    entropy: float = 0.15
    surprise: float = 0.15
    persistence: float = 0.10

    def validate(self) -> None:
        values = (
            self.usage_ratio,
            self.momentum,
            self.entropy,
            self.surprise,
            self.persistence,
        )

        if any(value < 0.0 for value in values):
            raise ValueError(
                "Pressure weights must be non-negative."
            )

        total = sum(values)

        if total <= 0.0:
            raise ValueError(
                "At least one pressure weight must be positive."
            )


@dataclass(frozen=True, slots=True)
class PressureThresholds:
    """Thresholds used only to label an observation."""

    watch: float = 0.50
    high: float = 0.70
    critical: float = 0.85
    persistence: float = 0.70

    def validate(self) -> None:
        values = (
            self.watch,
            self.high,
            self.critical,
            self.persistence,
        )

        if any(
            value < 0.0 or value > 1.0
            for value in values
        ):
            raise ValueError(
                "Pressure thresholds must be between 0 and 1."
            )

        if not (
            self.watch
            <= self.high
            <= self.critical
        ):
            raise ValueError(
                "Pressure thresholds must be ordered: "
                "watch <= high <= critical."
            )


@dataclass(frozen=True, slots=True)
class PressureObservationInput:
    """Normalized source data required to calculate one observation.

    No storage object is accepted here. Callers must provide explicit,
    already-selected hot-site or simulated measurements.
    """

    scope_id: str
    used_items: int
    capacity: int
    usage_samples: Sequence[int] = ()
    term_frequencies: Mapping[str, int] | None = None
    surprise_samples: Sequence[float] = ()
    previous_pressure_samples: Sequence[float] = ()
    observed_at: str | None = None

    def validate(self) -> None:
        if not self.scope_id.strip():
            raise ValueError(
                "scope_id must be a non-empty string."
            )

        if self.used_items < 0:
            raise ValueError(
                "used_items must be non-negative."
            )

        if self.capacity <= 0:
            raise ValueError(
                "capacity must be strictly positive."
            )

        if any(
            sample < 0
            for sample in self.usage_samples
        ):
            raise ValueError(
                "usage_samples must be non-negative."
            )

        if self.term_frequencies is not None:
            if any(
                count < 0
                for count in self.term_frequencies.values()
            ):
                raise ValueError(
                    "term frequencies must be non-negative."
                )

        for name, values in (
            (
                "surprise_samples",
                self.surprise_samples,
            ),
            (
                "previous_pressure_samples",
                self.previous_pressure_samples,
            ),
        ):
            if any(
                value < 0.0 or value > 1.0
                for value in values
            ):
                raise ValueError(
                    f"{name} values must be between 0 and 1."
                )


@dataclass(frozen=True, slots=True)
class PressureComponents:
    """Normalized values used to calculate memory pressure."""

    usage_ratio: float
    momentum: float
    entropy: float
    surprise: float
    persistence: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PressureObservation:
    """Immutable, explainable result of one pressure calculation."""

    observation_id: str
    scope_id: str
    observed_at: str
    level: PressureLevel
    memory_pressure: float
    components: PressureComponents
    used_items: int
    capacity: int
    sample_sizes: Mapping[str, int]
    explanation: tuple[str, ...]
    schema_version: int = 1
    observation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "scope_id": self.scope_id,
            "observed_at": self.observed_at,
            "level": self.level.value,
            "memory_pressure": self.memory_pressure,
            "components": self.components.as_dict(),
            "used_items": self.used_items,
            "capacity": self.capacity,
            "sample_sizes": dict(self.sample_sizes),
            "explanation": list(self.explanation),
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
        }


def utc_now_iso() -> str:
    """Return a stable UTC ISO-8601 timestamp."""

    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True, slots=True)
class TopicTerm:
    """One normalized term contributing to a dynamic topic block."""

    term: str
    count: int
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "count": self.count,
            "weight": self.weight,
        }


@dataclass(frozen=True, slots=True)
class TopicBlockRoutingObservation:
    """Action-free observation of a possible topic-block routing."""

    routing_id: str
    block_id: str
    label: str
    confidence: float
    matched_terms: tuple[str, ...]
    content_digest: str
    explanation: tuple[str, ...]
    observed_at: str
    schema_version: int = 1
    observation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_id": self.routing_id,
            "block_id": self.block_id,
            "label": self.label,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "content_digest": self.content_digest,
            "explanation": list(self.explanation),
            "observed_at": self.observed_at,
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
        }


@dataclass(frozen=True, slots=True)
class TopicBlockObservation:
    """Immutable observation of one dynamically inferred topic block."""

    block_id: str
    label: str
    terms: tuple[TopicTerm, ...]
    capacity: int
    used_items: int
    usage_ratio: float
    importance: float
    observed_item_ids: tuple[str, ...]
    created_at: str
    updated_at: str
    routing: TopicBlockRoutingObservation
    schema_version: int = 1
    observation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "terms": [
                term.to_dict()
                for term in self.terms
            ],
            "capacity": self.capacity,
            "used_items": self.used_items,
            "usage_ratio": self.usage_ratio,
            "importance": self.importance,
            "observed_item_ids": list(
                self.observed_item_ids
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "routing": self.routing.to_dict(),
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
        }


@dataclass(frozen=True, slots=True)
class TopicBlockInput:
    """Explicit source data used to infer one dynamic topic block."""

    content: str
    item_id: str
    metadata_terms: Sequence[str] = ()
    importance: float = 0.5
    capacity: int = 100
    used_items: int = 1
    observed_at: str | None = None

    def validate(self) -> None:
        if not self.content.strip():
            raise ValueError(
                "content must be a non-empty string."
            )

        if not self.item_id.strip():
            raise ValueError(
                "item_id must be a non-empty string."
            )

        if self.capacity <= 0:
            raise ValueError(
                "capacity must be strictly positive."
            )

        if self.used_items < 0:
            raise ValueError(
                "used_items must be non-negative."
            )

        if (
            self.importance < 0.0
            or self.importance > 1.0
        ):
            raise ValueError(
                "importance must be between 0 and 1."
            )
