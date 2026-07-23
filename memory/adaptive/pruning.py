"""Dry-run soft-pruning plans for validated hot memories.

This module never deletes, weakens, deactivates, or rewrites a memory. It
does not read or mutate the cold site. It only creates explainable plans from
explicit hot-memory measurements.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from memory.adaptive.contracts import (
    HotMemoryPruningInput,
    PressureObservation,
    SoftPruningAction,
    SoftPruningPlan,
    SoftPruningPolicy,
    SoftPruningRecommendation,
    utc_now_iso,
)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _retention_components(
    memory: HotMemoryPruningInput,
    policy: SoftPruningPolicy,
) -> dict[str, float]:
    recency = 1.0 - _clamp_unit(
        memory.age_days
        / policy.maximum_age_days
    )

    access = _clamp_unit(
        memory.access_count
        / policy.access_saturation
    )

    return {
        "importance": memory.importance,
        "recency": recency,
        "access": access,
        "retrieval": memory.retrieval_score,
    }


def calculate_retention_score(
    memory: HotMemoryPruningInput,
    *,
    policy: SoftPruningPolicy | None = None,
) -> float:
    """Calculate a normalized retention score for one hot memory."""

    memory.validate()

    resolved_policy = policy or SoftPruningPolicy()
    resolved_policy.validate()

    components = _retention_components(
        memory,
        resolved_policy,
    )

    weighted_sum = (
        components["importance"]
        * resolved_policy.importance_weight
        + components["recency"]
        * resolved_policy.recency_weight
        + components["access"]
        * resolved_policy.access_weight
        + components["retrieval"]
        * resolved_policy.retrieval_weight
    )

    total_weight = (
        resolved_policy.importance_weight
        + resolved_policy.recency_weight
        + resolved_policy.access_weight
        + resolved_policy.retrieval_weight
    )

    return _clamp_unit(
        weighted_sum / total_weight
    )


def _protection_reasons(
    memory: HotMemoryPruningInput,
    policy: SoftPruningPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if memory.pinned:
        reasons.append("pinned")

    if not memory.human_validated:
        reasons.append(
            "not_eligible_unvalidated"
        )

    if (
        memory.importance
        >= policy.protected_importance
    ):
        reasons.append("high_importance")

    if (
        memory.age_days
        <= policy.protected_recency_days
    ):
        reasons.append("recent")

    if (
        memory.access_count
        >= policy.protected_access_count
    ):
        reasons.append("frequently_accessed")

    return tuple(reasons)


def recommend_soft_pruning(
    memory: HotMemoryPruningInput,
    pressure: PressureObservation,
    *,
    policy: SoftPruningPolicy | None = None,
) -> SoftPruningRecommendation:
    """Create one action-free hot-site pruning recommendation."""

    memory.validate()

    resolved_policy = policy or SoftPruningPolicy()
    resolved_policy.validate()

    if pressure.scope_id != memory.block_id:
        raise ValueError(
            "Pressure scope_id must match the memory block_id."
        )

    retention_score = calculate_retention_score(
        memory,
        policy=resolved_policy,
    )

    components = _retention_components(
        memory,
        resolved_policy,
    )

    protection_reasons = _protection_reasons(
        memory,
        resolved_policy,
    )

    protected = bool(protection_reasons)

    if not memory.active:
        action = SoftPruningAction.KEEP
        decision_reason = (
            "Memory is already inactive; no additional "
            "dry-run action is proposed."
        )
    elif protected:
        action = SoftPruningAction.KEEP
        decision_reason = (
            "Memory is protected by retention safeguards."
        )
    elif (
        pressure.memory_pressure
        < resolved_policy.minimum_pressure
    ):
        action = SoftPruningAction.KEEP
        decision_reason = (
            "Observed pressure is below the pruning threshold."
        )
    elif (
        retention_score
        <= resolved_policy.deactivate_score_threshold
    ):
        action = SoftPruningAction.DEACTIVATE
        decision_reason = (
            "Persistent pressure and very low retention "
            "support a dry-run deactivation recommendation."
        )
    elif (
        retention_score
        <= resolved_policy.weaken_score_threshold
    ):
        action = SoftPruningAction.WEAKEN
        decision_reason = (
            "Persistent pressure and low retention "
            "support a dry-run weakening recommendation."
        )
    else:
        action = SoftPruningAction.KEEP
        decision_reason = (
            "Retention score remains above pruning thresholds."
        )

    explanation = (
        decision_reason,
        (
            f"retention_score={retention_score:.4f}, "
            f"memory_pressure="
            f"{pressure.memory_pressure:.4f}."
        ),
        (
            "This recommendation applies to the logical hot site "
            "only; the cold archive remains untouched."
        ),
        (
            "No weakening, deactivation, physical deletion, "
            "or storage mutation was performed."
        ),
    )

    return SoftPruningRecommendation(
        memory_id=memory.memory_id,
        block_id=memory.block_id,
        action=action,
        retention_score=retention_score,
        pressure=pressure.memory_pressure,
        protected=protected,
        protection_reasons=protection_reasons,
        scoring_components=components,
        explanation=explanation,
    )


def plan_soft_pruning(
    *,
    scope_id: str,
    memories: Sequence[HotMemoryPruningInput],
    pressure: PressureObservation,
    policy: SoftPruningPolicy | None = None,
    plan_id: str | None = None,
    created_at: str | None = None,
) -> SoftPruningPlan:
    """Create a deterministic dry-run plan for one hot-site scope."""

    if not scope_id.strip():
        raise ValueError(
            "scope_id must be a non-empty string."
        )

    if pressure.scope_id != scope_id:
        raise ValueError(
            "Pressure scope_id must match plan scope_id."
        )

    resolved_policy = policy or SoftPruningPolicy()
    resolved_policy.validate()

    seen_memory_ids: set[str] = set()
    recommendations: list[
        SoftPruningRecommendation
    ] = []

    for memory in memories:
        if memory.memory_id in seen_memory_ids:
            raise ValueError(
                "Duplicate logical memory_id in pruning input: "
                f"{memory.memory_id}"
            )

        seen_memory_ids.add(memory.memory_id)

        recommendations.append(
            recommend_soft_pruning(
                memory,
                pressure,
                policy=resolved_policy,
            )
        )

    recommendations.sort(
        key=lambda recommendation: (
            recommendation.retention_score,
            recommendation.memory_id,
        )
    )

    return SoftPruningPlan(
        plan_id=(
            plan_id
            or f"pruning_{uuid.uuid4().hex}"
        ),
        scope_id=scope_id,
        pressure_observation_id=(
            pressure.observation_id
        ),
        pressure=pressure.memory_pressure,
        recommendations=tuple(
            recommendations
        ),
        created_at=created_at or utc_now_iso(),
    )
