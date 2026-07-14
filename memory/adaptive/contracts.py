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

@dataclass(frozen=True, slots=True)
class ControlledTopicRouting:
    """Topic metadata attached during explicit human validation.

    This contract describes a logical routing annotation only. It does not
    move a memory, validate a candidate, resize Titan, prune data, search
    cold history, or alter retrieval behavior.
    """

    block_id: str
    label: str
    confidence: float
    matched_terms: tuple[str, ...]
    routing_id: str
    observed_at: str
    observation_only: bool = True
    physical_partitioning: bool = False
    retrieval_behavior_changed: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "label": self.label,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "routing_id": self.routing_id,
            "observed_at": self.observed_at,
            "observation_only": self.observation_only,
            "physical_partitioning": self.physical_partitioning,
            "retrieval_behavior_changed": (
                self.retrieval_behavior_changed
            ),
            "schema_version": self.schema_version,
        }

class CapacityRecommendationLevel(str, Enum):
    """Strength of an action-free capacity recommendation."""

    KEEP = "keep"
    WATCH = "watch"
    EXPAND = "expand"


@dataclass(frozen=True, slots=True)
class CapacityPolicy:
    """Thresholds controlling dry-run expansion recommendations."""

    minimum_usage_ratio: float = 0.80
    minimum_memory_pressure: float = 0.70
    minimum_persistence: float = 0.60
    minimum_momentum: float = 0.05
    minimum_entropy: float = 0.55
    minimum_surprise: float = 0.55
    minimum_supporting_signals: int = 2
    minimum_increment: int = 10
    normal_growth_factor: float = 1.25
    strong_growth_factor: float = 1.50
    maximum_growth_factor: float = 2.00

    def validate(self) -> None:
        normalized_values = (
            self.minimum_usage_ratio,
            self.minimum_memory_pressure,
            self.minimum_persistence,
            self.minimum_momentum,
            self.minimum_entropy,
            self.minimum_surprise,
        )

        if any(
            value < 0.0 or value > 1.0
            for value in normalized_values
        ):
            raise ValueError(
                "Normalized capacity-policy thresholds "
                "must be between 0 and 1."
            )

        if self.minimum_supporting_signals < 1:
            raise ValueError(
                "minimum_supporting_signals must be positive."
            )

        if self.minimum_increment < 1:
            raise ValueError(
                "minimum_increment must be positive."
            )

        if self.normal_growth_factor < 1.0:
            raise ValueError(
                "normal_growth_factor must be at least 1."
            )

        if (
            self.strong_growth_factor
            < self.normal_growth_factor
        ):
            raise ValueError(
                "strong_growth_factor must be greater than "
                "or equal to normal_growth_factor."
            )

        if (
            self.maximum_growth_factor
            < self.strong_growth_factor
        ):
            raise ValueError(
                "maximum_growth_factor must be greater than "
                "or equal to strong_growth_factor."
            )


@dataclass(frozen=True, slots=True)
class CapacityRecommendationInput:
    """Explicit inputs for one dry-run capacity evaluation."""

    block_id: str
    current_capacity: int
    used_items: int
    pressure: PressureObservation
    evaluated_at: str | None = None

    def validate(self) -> None:
        if not self.block_id.strip():
            raise ValueError(
                "block_id must be a non-empty string."
            )

        if self.current_capacity <= 0:
            raise ValueError(
                "current_capacity must be strictly positive."
            )

        if self.used_items < 0:
            raise ValueError(
                "used_items must be non-negative."
            )

        if self.pressure.scope_id != self.block_id:
            raise ValueError(
                "Pressure scope_id must match block_id."
            )


@dataclass(frozen=True, slots=True)
class CapacityRecommendation:
    """Immutable recommendation that never applies capacity changes."""

    recommendation_id: str
    block_id: str
    level: CapacityRecommendationLevel
    current_capacity: int
    recommended_capacity: int
    recommended_increment: int
    usage_ratio: float
    memory_pressure: float
    persistence: float
    supporting_signals: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    explanation: tuple[str, ...]
    evaluated_at: str
    dry_run: bool = True
    applied: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "block_id": self.block_id,
            "level": self.level.value,
            "current_capacity": self.current_capacity,
            "recommended_capacity": self.recommended_capacity,
            "recommended_increment": self.recommended_increment,
            "usage_ratio": self.usage_ratio,
            "memory_pressure": self.memory_pressure,
            "persistence": self.persistence,
            "supporting_signals": list(
                self.supporting_signals
            ),
            "blocking_reasons": list(
                self.blocking_reasons
            ),
            "explanation": list(self.explanation),
            "evaluated_at": self.evaluated_at,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "schema_version": self.schema_version,
        }

class SoftPruningAction(str, Enum):
    """Action proposed by a dry-run hot-site pruning plan."""

    KEEP = "keep"
    WEAKEN = "weaken"
    DEACTIVATE = "deactivate"


@dataclass(frozen=True, slots=True)
class SoftPruningPolicy:
    """Thresholds used to create non-applied pruning recommendations."""

    minimum_pressure: float = 0.70
    weaken_score_threshold: float = 0.42
    deactivate_score_threshold: float = 0.22
    protected_importance: float = 0.85
    protected_recency_days: float = 7.0
    protected_access_count: int = 20
    maximum_age_days: float = 365.0
    access_saturation: int = 25

    importance_weight: float = 0.35
    recency_weight: float = 0.25
    access_weight: float = 0.20
    retrieval_weight: float = 0.20

    def validate(self) -> None:
        normalized_values = (
            self.minimum_pressure,
            self.weaken_score_threshold,
            self.deactivate_score_threshold,
            self.protected_importance,
            self.importance_weight,
            self.recency_weight,
            self.access_weight,
            self.retrieval_weight,
        )

        if any(
            value < 0.0 or value > 1.0
            for value in normalized_values
        ):
            raise ValueError(
                "Normalized pruning policy values "
                "must be between 0 and 1."
            )

        if (
            self.deactivate_score_threshold
            > self.weaken_score_threshold
        ):
            raise ValueError(
                "deactivate_score_threshold must be lower than "
                "or equal to weaken_score_threshold."
            )

        if self.protected_recency_days < 0.0:
            raise ValueError(
                "protected_recency_days must be non-negative."
            )

        if self.protected_access_count < 0:
            raise ValueError(
                "protected_access_count must be non-negative."
            )

        if self.maximum_age_days <= 0.0:
            raise ValueError(
                "maximum_age_days must be strictly positive."
            )

        if self.access_saturation <= 0:
            raise ValueError(
                "access_saturation must be strictly positive."
            )

        total_weight = (
            self.importance_weight
            + self.recency_weight
            + self.access_weight
            + self.retrieval_weight
        )

        if total_weight <= 0.0:
            raise ValueError(
                "At least one retention weight must be positive."
            )


@dataclass(frozen=True, slots=True)
class HotMemoryPruningInput:
    """Explicit hot-memory measurements used by the pruning planner."""

    memory_id: str
    block_id: str
    importance: float
    access_count: int
    age_days: float
    retrieval_score: float
    active: bool = True
    pinned: bool = False
    human_validated: bool = True
    metadata: Mapping[str, Any] | None = None

    def validate(self) -> None:
        if not self.memory_id.strip():
            raise ValueError(
                "memory_id must be a non-empty string."
            )

        if not self.block_id.strip():
            raise ValueError(
                "block_id must be a non-empty string."
            )

        if (
            self.importance < 0.0
            or self.importance > 1.0
        ):
            raise ValueError(
                "importance must be between 0 and 1."
            )

        if self.access_count < 0:
            raise ValueError(
                "access_count must be non-negative."
            )

        if self.age_days < 0.0:
            raise ValueError(
                "age_days must be non-negative."
            )

        if (
            self.retrieval_score < 0.0
            or self.retrieval_score > 1.0
        ):
            raise ValueError(
                "retrieval_score must be between 0 and 1."
            )


@dataclass(frozen=True, slots=True)
class SoftPruningRecommendation:
    """One dry-run recommendation for one logical hot memory."""

    memory_id: str
    block_id: str
    action: SoftPruningAction
    retention_score: float
    pressure: float
    protected: bool
    protection_reasons: tuple[str, ...]
    scoring_components: Mapping[str, float]
    explanation: tuple[str, ...]
    hot_site_only: bool = True
    physical_deletion: bool = False
    dry_run: bool = True
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "block_id": self.block_id,
            "action": self.action.value,
            "retention_score": self.retention_score,
            "pressure": self.pressure,
            "protected": self.protected,
            "protection_reasons": list(
                self.protection_reasons
            ),
            "scoring_components": dict(
                self.scoring_components
            ),
            "explanation": list(self.explanation),
            "hot_site_only": self.hot_site_only,
            "physical_deletion": self.physical_deletion,
            "dry_run": self.dry_run,
            "applied": self.applied,
        }


@dataclass(frozen=True, slots=True)
class SoftPruningPlan:
    """Immutable dry-run plan for a hot-site or topic-block scope."""

    plan_id: str
    scope_id: str
    pressure_observation_id: str
    pressure: float
    recommendations: tuple[
        SoftPruningRecommendation,
        ...
    ]
    created_at: str
    hot_site_only: bool = True
    cold_site_untouched: bool = True
    physical_deletion: bool = False
    dry_run: bool = True
    applied: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "scope_id": self.scope_id,
            "pressure_observation_id": (
                self.pressure_observation_id
            ),
            "pressure": self.pressure,
            "recommendations": [
                recommendation.to_dict()
                for recommendation
                in self.recommendations
            ],
            "created_at": self.created_at,
            "hot_site_only": self.hot_site_only,
            "cold_site_untouched": (
                self.cold_site_untouched
            ),
            "physical_deletion": (
                self.physical_deletion
            ),
            "dry_run": self.dry_run,
            "applied": self.applied,
            "schema_version": self.schema_version,
        }
