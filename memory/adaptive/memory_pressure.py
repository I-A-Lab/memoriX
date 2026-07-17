"""Deterministic per-memory pressure metrics.

This module evaluates explicit hot-site metadata only. It performs no storage
mutation, no cold-site access, no retrieval fallback, and no pruning action.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Any, Iterable, Mapping

from memory.adaptive.contracts import PressureLevel, PressureThresholds, utc_now_iso


def normalize_unit(value: float | int | None, *, default: float = 0.0) -> float:
    """Return one finite float clamped to [0, 1]."""

    if value is None:
        value = default
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = float(default)
    if not math.isfinite(resolved):
        resolved = float(default)
    return max(0.0, min(1.0, resolved))


def normalize_non_negative(value: float | int | None, *, default: float = 0.0) -> float:
    """Return one finite non-negative float."""

    if value is None:
        value = default
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = float(default)
    if not math.isfinite(resolved):
        resolved = float(default)
    return max(0.0, resolved)


def normalize_age(age_days: float | int | None, *, horizon_days: float = 365.0) -> float:
    """Normalize age against a configurable positive horizon."""

    horizon = normalize_non_negative(horizon_days)
    if horizon <= 0.0:
        raise ValueError("horizon_days must be strictly positive.")
    return normalize_unit(normalize_non_negative(age_days) / horizon)


def normalize_low_usage(access_count: int | float | None, *, saturation_count: float = 20.0) -> float:
    """Return pressure caused by low access frequency."""

    saturation = normalize_non_negative(saturation_count)
    if saturation <= 0.0:
        raise ValueError("saturation_count must be strictly positive.")
    usage = normalize_unit(normalize_non_negative(access_count) / saturation)
    return 1.0 - usage


@dataclass(frozen=True, slots=True)
class MemoryPressureWeights:
    age: float = 0.25
    low_usage: float = 0.20
    low_importance: float = 0.15
    low_momentum: float = 0.10
    low_surprise: float = 0.10
    inactive: float = 0.10
    replaced: float = 0.10

    def validate(self) -> None:
        values = tuple(asdict(self).values())
        if any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValueError("Memory-pressure weights must be finite and non-negative.")
        if sum(values) <= 0.0:
            raise ValueError("At least one memory-pressure weight must be positive.")


@dataclass(frozen=True, slots=True)
class MemoryPressureInput:
    memory_id: str
    age_days: float = 0.0
    access_count: int = 0
    importance: float = 0.5
    momentum: float = 0.0
    surprise: float = 0.0
    active: bool = True
    replaced: bool = False
    protected: bool = False
    metadata: Mapping[str, Any] | None = None
    observed_at: str | None = None

    def validate(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must be a non-empty string.")


@dataclass(frozen=True, slots=True)
class MemoryPressureComponents:
    age: float
    low_usage: float
    low_importance: float
    low_momentum: float
    low_surprise: float
    inactive: float
    replaced: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryPressureAssessment:
    assessment_id: str
    memory_id: str
    observed_at: str
    pressure_score: float
    retention_score: float
    level: PressureLevel
    components: MemoryPressureComponents
    protected: bool
    recommended_action: str
    reasons: tuple[str, ...]
    schema_version: int = 1
    observation_only: bool = True
    applies_changes: bool = False
    cold_site_accessed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "memory_id": self.memory_id,
            "observed_at": self.observed_at,
            "pressure_score": self.pressure_score,
            "retention_score": self.retention_score,
            "level": self.level.value,
            "components": self.components.to_dict(),
            "protected": self.protected,
            "recommended_action": self.recommended_action,
            "reasons": list(self.reasons),
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
            "applies_changes": self.applies_changes,
            "cold_site_accessed": self.cold_site_accessed,
        }


@dataclass(frozen=True, slots=True)
class HotSitePressureSnapshot:
    snapshot_id: str
    observed_at: str
    memory_count: int
    mean_pressure: float
    maximum_pressure: float
    level_counts: Mapping[str, int]
    protected_count: int
    inactive_count: int
    replaced_count: int
    pruning_candidate_count: int
    assessments: tuple[MemoryPressureAssessment, ...]
    schema_version: int = 1
    observation_only: bool = True
    applies_changes: bool = False
    cold_site_accessed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "observed_at": self.observed_at,
            "memory_count": self.memory_count,
            "mean_pressure": self.mean_pressure,
            "maximum_pressure": self.maximum_pressure,
            "level_counts": dict(self.level_counts),
            "protected_count": self.protected_count,
            "inactive_count": self.inactive_count,
            "replaced_count": self.replaced_count,
            "pruning_candidate_count": self.pruning_candidate_count,
            "assessments": [item.to_dict() for item in self.assessments],
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
            "applies_changes": self.applies_changes,
            "cold_site_accessed": self.cold_site_accessed,
        }


def _classify(score: float, thresholds: PressureThresholds) -> PressureLevel:
    thresholds.validate()
    if score >= thresholds.critical:
        return PressureLevel.CRITICAL
    if score >= thresholds.high:
        return PressureLevel.HIGH
    if score >= thresholds.watch:
        return PressureLevel.WATCH
    return PressureLevel.STABLE


def assess_memory_pressure(
    source: MemoryPressureInput,
    *,
    weights: MemoryPressureWeights | None = None,
    thresholds: PressureThresholds | None = None,
    age_horizon_days: float = 365.0,
    usage_saturation_count: float = 20.0,
    assessment_id: str | None = None,
) -> MemoryPressureAssessment:
    """Calculate one deterministic, explainable pressure assessment."""

    source.validate()
    resolved_weights = weights or MemoryPressureWeights()
    resolved_weights.validate()
    resolved_thresholds = thresholds or PressureThresholds()

    components = MemoryPressureComponents(
        age=normalize_age(source.age_days, horizon_days=age_horizon_days),
        low_usage=normalize_low_usage(source.access_count, saturation_count=usage_saturation_count),
        low_importance=1.0 - normalize_unit(source.importance, default=0.5),
        low_momentum=1.0 - normalize_unit(source.momentum),
        low_surprise=1.0 - normalize_unit(source.surprise),
        inactive=0.0 if source.active else 1.0,
        replaced=1.0 if source.replaced else 0.0,
    )

    component_values = components.to_dict()
    weight_values = asdict(resolved_weights)
    total_weight = sum(weight_values.values())
    pressure = sum(component_values[name] * weight_values[name] for name in component_values) / total_weight
    pressure = normalize_unit(pressure)
    retention = 1.0 - pressure
    level = _classify(pressure, resolved_thresholds)

    reasons = tuple(
        name
        for name, value in sorted(component_values.items(), key=lambda item: (-item[1], item[0]))
        if value >= 0.5
    )

    if source.protected:
        action = "keep_protected"
    elif level is PressureLevel.CRITICAL:
        action = "deactivate_candidate"
    elif level is PressureLevel.HIGH:
        action = "review_for_soft_pruning"
    else:
        action = "keep"

    return MemoryPressureAssessment(
        assessment_id=assessment_id or f"memory_pressure_{uuid.uuid4().hex}",
        memory_id=source.memory_id,
        observed_at=source.observed_at or utc_now_iso(),
        pressure_score=pressure,
        retention_score=retention,
        level=level,
        components=components,
        protected=source.protected,
        recommended_action=action,
        reasons=reasons,
    )


def observe_hot_site_pressure(
    memories: Iterable[MemoryPressureInput],
    *,
    weights: MemoryPressureWeights | None = None,
    thresholds: PressureThresholds | None = None,
    observed_at: str | None = None,
    snapshot_id: str | None = None,
) -> HotSitePressureSnapshot:
    """Aggregate individual assessments without mutating any storage."""

    resolved_observed_at = observed_at or utc_now_iso()
    resolved_memories = tuple(memories)
    assessments = tuple(
        sorted(
            (
                assess_memory_pressure(
                    memory,
                    weights=weights,
                    thresholds=thresholds,
                    assessment_id=f"assessment_{memory.memory_id}",
                )
                for memory in resolved_memories
            ),
            key=lambda item: item.memory_id,
        )
    )
    levels = {level.value: 0 for level in PressureLevel}
    for item in assessments:
        levels[item.level.value] += 1

    pressures = [item.pressure_score for item in assessments]
    return HotSitePressureSnapshot(
        snapshot_id=snapshot_id or f"hot_site_pressure_{uuid.uuid4().hex}",
        observed_at=resolved_observed_at,
        memory_count=len(assessments),
        mean_pressure=fmean(pressures) if pressures else 0.0,
        maximum_pressure=max(pressures, default=0.0),
        level_counts=levels,
        protected_count=sum(item.protected for item in assessments),
        inactive_count=sum(not memory.active for memory in resolved_memories),
        replaced_count=sum(item.components.replaced == 1.0 for item in assessments),
        pruning_candidate_count=sum(item.recommended_action == "deactivate_candidate" for item in assessments),
        assessments=assessments,
    )
