"""Dry-run dynamic-capacity recommendations.

This module never resizes Titan or a topic block. It produces explainable
recommendations from an explicit pressure observation.

A high usage ratio alone is insufficient. Expansion requires persistent
pressure and multiple supporting signals.
"""

from __future__ import annotations

import math
import uuid

from memory.adaptive.contracts import (
    CapacityPolicy,
    CapacityRecommendation,
    CapacityRecommendationInput,
    CapacityRecommendationLevel,
    utc_now_iso,
)


def _supporting_signals(
    source: CapacityRecommendationInput,
    policy: CapacityPolicy,
) -> tuple[str, ...]:
    components = source.pressure.components
    signals: list[str] = []

    if components.momentum >= policy.minimum_momentum:
        signals.append("momentum")

    if components.entropy >= policy.minimum_entropy:
        signals.append("entropy")

    if components.surprise >= policy.minimum_surprise:
        signals.append("surprise")

    return tuple(signals)


def _blocking_reasons(
    source: CapacityRecommendationInput,
    policy: CapacityPolicy,
    supporting_signals: tuple[str, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []

    usage_ratio = min(
        1.0,
        source.used_items
        / source.current_capacity,
    )

    if usage_ratio < policy.minimum_usage_ratio:
        reasons.append(
            "usage_ratio_below_threshold"
        )

    if (
        source.pressure.memory_pressure
        < policy.minimum_memory_pressure
    ):
        reasons.append(
            "memory_pressure_below_threshold"
        )

    if (
        source.pressure.components.persistence
        < policy.minimum_persistence
    ):
        reasons.append(
            "pressure_not_persistent"
        )

    if (
        len(supporting_signals)
        < policy.minimum_supporting_signals
    ):
        reasons.append(
            "insufficient_supporting_signals"
        )

    return tuple(reasons)


def _growth_factor(
    source: CapacityRecommendationInput,
    policy: CapacityPolicy,
    supporting_signals: tuple[str, ...],
) -> float:
    """Choose a bounded growth factor for an approved recommendation."""

    components = source.pressure.components

    strong_pressure = (
        source.pressure.memory_pressure >= 0.85
        and components.persistence >= 0.80
        and len(supporting_signals) >= 3
    )

    factor = (
        policy.strong_growth_factor
        if strong_pressure
        else policy.normal_growth_factor
    )

    return min(
        factor,
        policy.maximum_growth_factor,
    )


def _recommended_capacity(
    current_capacity: int,
    growth_factor: float,
    minimum_increment: int,
) -> int:
    multiplicative_capacity = math.ceil(
        current_capacity * growth_factor
    )

    additive_capacity = (
        current_capacity
        + minimum_increment
    )

    return max(
        multiplicative_capacity,
        additive_capacity,
    )


def recommend_dynamic_capacity(
    source: CapacityRecommendationInput,
    *,
    policy: CapacityPolicy | None = None,
    recommendation_id: str | None = None,
) -> CapacityRecommendation:
    """Produce one explainable dry-run recommendation."""

    source.validate()

    resolved_policy = policy or CapacityPolicy()
    resolved_policy.validate()

    usage_ratio = min(
        1.0,
        source.used_items
        / source.current_capacity,
    )

    supporting_signals = _supporting_signals(
        source,
        resolved_policy,
    )

    blocking_reasons = _blocking_reasons(
        source,
        resolved_policy,
        supporting_signals,
    )

    if blocking_reasons:
        near_capacity = (
            usage_ratio
            >= resolved_policy.minimum_usage_ratio
        )

        level = (
            CapacityRecommendationLevel.WATCH
            if near_capacity
            else CapacityRecommendationLevel.KEEP
        )

        recommended_capacity = (
            source.current_capacity
        )
    else:
        level = (
            CapacityRecommendationLevel.EXPAND
        )

        recommended_capacity = (
            _recommended_capacity(
                source.current_capacity,
                _growth_factor(
                    source,
                    resolved_policy,
                    supporting_signals,
                ),
                resolved_policy.minimum_increment,
            )
        )

    increment = (
        recommended_capacity
        - source.current_capacity
    )

    explanation = (
        (
            f"Capacity recommendation is "
            f"{level.value} for {source.block_id}."
        ),
        (
            f"Observed usage_ratio={usage_ratio:.4f}, "
            f"memory_pressure="
            f"{source.pressure.memory_pressure:.4f}, "
            f"persistence="
            f"{source.pressure.components.persistence:.4f}."
        ),
        (
            "Supporting signals: "
            + (
                ", ".join(supporting_signals)
                if supporting_signals
                else "none"
            )
            + "."
        ),
        (
            "No capacity was modified. This result is "
            "a dry-run recommendation only."
        ),
    )

    return CapacityRecommendation(
        recommendation_id=(
            recommendation_id
            or f"capacity_{uuid.uuid4().hex}"
        ),
        block_id=source.block_id,
        level=level,
        current_capacity=source.current_capacity,
        recommended_capacity=(
            recommended_capacity
        ),
        recommended_increment=increment,
        usage_ratio=usage_ratio,
        memory_pressure=(
            source.pressure.memory_pressure
        ),
        persistence=(
            source.pressure.components.persistence
        ),
        supporting_signals=(
            supporting_signals
        ),
        blocking_reasons=blocking_reasons,
        explanation=explanation,
        evaluated_at=(
            source.evaluated_at
            or utc_now_iso()
        ),
    )
