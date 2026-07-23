"""Global dry-run controller for adaptive hot-site recommendations.

The controller assembles pressure observations, capacity recommendations and
soft-pruning plans. It never applies the proposed actions.
"""

from __future__ import annotations

import uuid

from memory.adaptive.capacity import (
    recommend_dynamic_capacity,
)
from memory.adaptive.contracts import (
    AdaptiveControllerDecision,
    AdaptiveControllerInput,
    AdaptiveDecisionStatus,
    CapacityPolicy,
    CapacityRecommendationInput,
    CapacityRecommendationLevel,
    PressureObservationInput,
    PressureThresholds,
    PressureWeights,
    SoftPruningAction,
    SoftPruningPolicy,
    utc_now_iso,
)
from memory.adaptive.pressure import (
    observe_memory_pressure,
)
from memory.adaptive.pruning import (
    plan_soft_pruning,
)


def _recommended_actions(
    *,
    capacity_level: CapacityRecommendationLevel,
    pruning_actions: tuple[SoftPruningAction, ...],
) -> tuple[str, ...]:
    actions: list[str] = []

    if capacity_level is CapacityRecommendationLevel.EXPAND:
        actions.append(
            "recommend_capacity_expansion"
        )

    if SoftPruningAction.WEAKEN in pruning_actions:
        actions.append(
            "recommend_hot_memory_weakening"
        )

    if SoftPruningAction.DEACTIVATE in pruning_actions:
        actions.append(
            "recommend_hot_memory_deactivation"
        )

    return tuple(actions)


def _blocked_actions() -> tuple[str, ...]:
    return (
        "automatic_capacity_resize",
        "automatic_soft_forget",
        "automatic_deactivation",
        "physical_memory_deletion",
        "cold_site_mutation",
        "cold_to_hot_rehydration",
        "retrieval_contract_change",
        "automatic_candidate_validation",
    )


def _decision_status(
    *,
    pressure_level: str,
    recommended_actions: tuple[str, ...],
) -> AdaptiveDecisionStatus:
    if recommended_actions:
        return (
            AdaptiveDecisionStatus.ACTIONS_RECOMMENDED
        )

    if pressure_level in {
        "watch",
        "high",
        "critical",
    }:
        return AdaptiveDecisionStatus.WATCH

    return AdaptiveDecisionStatus.STABLE


def evaluate_adaptive_controller(
    source: AdaptiveControllerInput,
    *,
    pressure_weights: PressureWeights | None = None,
    pressure_thresholds: PressureThresholds | None = None,
    capacity_policy: CapacityPolicy | None = None,
    pruning_policy: SoftPruningPolicy | None = None,
    decision_id: str | None = None,
) -> AdaptiveControllerDecision:
    """Evaluate one complete adaptive cycle without applying actions."""

    source.validate()

    created_at = source.observed_at or utc_now_iso()

    pressure = observe_memory_pressure(
        PressureObservationInput(
            scope_id=source.scope_id,
            used_items=source.used_items,
            capacity=source.current_capacity,
            usage_samples=source.usage_samples,
            term_frequencies=source.term_frequencies,
            surprise_samples=source.surprise_samples,
            previous_pressure_samples=(
                source.previous_pressure_samples
            ),
            observed_at=created_at,
        ),
        weights=pressure_weights,
        thresholds=pressure_thresholds,
    )

    capacity = recommend_dynamic_capacity(
        CapacityRecommendationInput(
            block_id=source.scope_id,
            current_capacity=(
                source.current_capacity
            ),
            used_items=source.used_items,
            pressure=pressure,
            evaluated_at=created_at,
        ),
        policy=capacity_policy,
    )

    pruning = plan_soft_pruning(
        scope_id=source.scope_id,
        memories=source.memories,
        pressure=pressure,
        policy=pruning_policy,
        created_at=created_at,
    )

    pruning_actions = tuple(
        recommendation.action
        for recommendation
        in pruning.recommendations
    )

    recommended_actions = _recommended_actions(
        capacity_level=capacity.level,
        pruning_actions=pruning_actions,
    )

    status = _decision_status(
        pressure_level=pressure.level.value,
        recommended_actions=recommended_actions,
    )

    explanation = (
        (
            f"Adaptive status is {status.value} "
            f"for scope {source.scope_id}."
        ),
        (
            f"Observed pressure="
            f"{pressure.memory_pressure:.4f} "
            f"({pressure.level.value})."
        ),
        (
            f"Capacity recommendation="
            f"{capacity.level.value}; "
            f"pruning recommendations="
            f"{len(pruning.recommendations)}."
        ),
        (
            "All outputs remain dry-run recommendations. "
            "No adaptive action was applied."
        ),
    )

    return AdaptiveControllerDecision(
        decision_id=(
            decision_id
            or f"adaptive_{uuid.uuid4().hex}"
        ),
        scope_id=source.scope_id,
        status=status,
        pressure=pressure,
        capacity=capacity,
        pruning=pruning,
        recommended_actions=(
            recommended_actions
        ),
        blocked_actions=_blocked_actions(),
        explanation=explanation,
        created_at=created_at,
    )
