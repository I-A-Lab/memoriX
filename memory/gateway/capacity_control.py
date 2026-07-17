"""Capacity admission and controlled hot-site soft-pruning.

The helpers in this module never read or mutate the cold site. Candidate
admission is evaluated before any Titan write. Pruning application accepts
only an explicit dry-run plan and translates eligible DEACTIVATE
recommendations into logical hot-site soft-forget operations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from memory.adaptive import (
    SoftPruningAction,
    SoftPruningPlan,
)
from memory.data import ForgetAction
from memory.hot_site.titan_active_memory import HotSiteTitanMemory


class CapacityAdmissionError(RuntimeError):
    """Raised when a pending candidate cannot safely enter the hot site."""


class SoftPruningApplicationError(RuntimeError):
    """Raised when a pruning plan cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class CapacityAdmissionDecision:
    """Explainable decision made before candidate validation writes."""

    allowed: bool
    active_items: int
    configured_capacity: int
    available_slots: int
    reason: str
    observation_only: bool = True
    applies_changes: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SoftPruningApplicationReport:
    """Outcome of explicitly applying eligible recommendations."""

    plan_id: str
    requested_deactivations: int
    applied_memory_ids: tuple[str, ...]
    skipped_memory_ids: tuple[str, ...]
    hot_site_only: bool = True
    cold_site_untouched: bool = True
    physical_deletion: bool = False
    applied: bool = True
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["applied_memory_ids"] = list(self.applied_memory_ids)
        payload["skipped_memory_ids"] = list(self.skipped_memory_ids)
        return payload


def evaluate_capacity_admission(
    hot_site: HotSiteTitanMemory,
    *,
    configured_capacity: int,
) -> CapacityAdmissionDecision:
    """Inspect active logical memories without performing any mutation."""

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")

    active_items = len(hot_site.list_memories(active_only=True))
    available_slots = max(0, configured_capacity - active_items)
    allowed = active_items < configured_capacity

    reason = (
        "Hot-site capacity is available."
        if allowed
        else "Hot-site capacity is exhausted; the candidate remains pending."
    )

    return CapacityAdmissionDecision(
        allowed=allowed,
        active_items=active_items,
        configured_capacity=configured_capacity,
        available_slots=available_slots,
        reason=reason,
    )


def require_capacity_admission(
    hot_site: HotSiteTitanMemory,
    *,
    configured_capacity: int,
) -> CapacityAdmissionDecision:
    """Return an allowed decision or raise before any candidate mutation."""

    decision = evaluate_capacity_admission(
        hot_site,
        configured_capacity=configured_capacity,
    )

    if not decision.allowed:
        raise CapacityAdmissionError(decision.reason)

    return decision


def apply_soft_pruning_plan(
    plan: SoftPruningPlan,
    hot_site: HotSiteTitanMemory,
    *,
    applied_by: str,
    reason: str,
    max_deactivations: int | None = None,
) -> SoftPruningApplicationReport:
    """Apply only safe DEACTIVATE actions from one explicit dry-run plan."""

    reviewer = applied_by.strip()
    explanation = reason.strip()

    if not reviewer:
        raise ValueError("applied_by must not be empty.")
    if not explanation:
        raise ValueError("reason must not be empty.")
    if max_deactivations is not None and max_deactivations <= 0:
        raise ValueError("max_deactivations must be positive when provided.")

    if not plan.dry_run:
        raise SoftPruningApplicationError("Only dry-run pruning plans are accepted.")
    if not plan.hot_site_only:
        raise SoftPruningApplicationError("The pruning plan must be hot-site-only.")
    if not plan.cold_site_untouched:
        raise SoftPruningApplicationError("The pruning plan must leave the cold site untouched.")
    if plan.physical_deletion:
        raise SoftPruningApplicationError("Physical deletion is forbidden.")
    if plan.applied:
        raise SoftPruningApplicationError("The pruning plan is already marked applied.")

    eligible = [
        recommendation
        for recommendation in plan.recommendations
        if recommendation.action is SoftPruningAction.DEACTIVATE
        and not recommendation.protected
        and recommendation.hot_site_only
        and not recommendation.physical_deletion
        and recommendation.dry_run
        and not recommendation.applied
    ]

    if max_deactivations is not None:
        eligible = eligible[:max_deactivations]

    known_active = {
        memory.memory_id
        for memory in hot_site.list_memories(active_only=True)
    }
    applied_ids: list[str] = []
    skipped_ids: list[str] = []

    for recommendation in eligible:
        if recommendation.memory_id not in known_active:
            skipped_ids.append(recommendation.memory_id)
            continue

        result = hot_site.soft_forget(
            recommendation.memory_id,
            validated_by=reviewer,
            reason=f"{explanation} Plan {plan.plan_id}.",
        )

        if result.action is not ForgetAction.DEACTIVATED:
            raise SoftPruningApplicationError(
                "A recommended memory was not deactivated: "
                f"{recommendation.memory_id}"
            )

        applied_ids.append(recommendation.memory_id)

    requested = sum(
        1
        for recommendation in plan.recommendations
        if recommendation.action is SoftPruningAction.DEACTIVATE
        and not recommendation.protected
    )

    return SoftPruningApplicationReport(
        plan_id=plan.plan_id,
        requested_deactivations=requested,
        applied_memory_ids=tuple(applied_ids),
        skipped_memory_ids=tuple(skipped_ids),
    )
