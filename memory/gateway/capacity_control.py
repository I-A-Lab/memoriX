"""Capacity admission and controlled hot-site soft-pruning.

The helpers in this module never read or mutate the cold site. Candidate
admission is evaluated before any Titan write. Pruning application accepts
only an explicit dry-run plan and translates eligible DEACTIVATE
recommendations into logical hot-site soft-forget operations.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass
from typing import Any

from memory.adaptive import (
    SoftPruningAction,
    SoftPruningPlan,
)
from memory.data import ForgetAction
from memory.gateway.capacity_operations import CapacityOperations
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
    required_slots: int = 1,
) -> CapacityAdmissionDecision:
    """Inspect active logical memories without performing any mutation. Admission reserves ``required_slots`` slots for one validated store, so a multi-unit validated memory only enters when every unit fits."""

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")

    active_items = len(hot_site.list_memories(active_only=True))
    available_slots = max(0, configured_capacity - active_items)
    allowed = available_slots >= required_slots

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


def effective_capacity(
    hot_site: HotSiteTitanMemory,
    *,
    configured_capacity: int,
) -> int:
    """Return the live usable capacity of the elastic hot site.

    The elastic hot site may currently hold more than the configured baseline
    after an expansion. The effective capacity is the larger of the configured
    capacity and the persisted current capacity.
    """

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")

    live = int(
        hot_site.capacity_status()["current_capacity"]
    )

    return max(configured_capacity, live)


def evaluate_effective_capacity_admission(
    hot_site: HotSiteTitanMemory,
    *,
    configured_capacity: int,
) -> CapacityAdmissionDecision:
    """Evaluate admission against the live elastic capacity.

    The decision reports the effective capacity as the capacity the admission
    was evaluated against.
    """

    capacity = effective_capacity(
        hot_site,
        configured_capacity=configured_capacity,
    )

    active_items = len(
        hot_site.list_memories(active_only=True)
    )
    available_slots = max(0, capacity - active_items)
    allowed = active_items < capacity

    reason = (
        "Hot-site capacity is available."
        if allowed
        else "Hot-site capacity is exhausted; the candidate remains pending."
    )

    return CapacityAdmissionDecision(
        allowed=allowed,
        active_items=active_items,
        configured_capacity=capacity,
        available_slots=available_slots,
        reason=reason,
    )


def ensure_expanded_capacity(
    hot_site: HotSiteTitanMemory,
    *,
    configured_capacity: int,
    required_slots: int = 1,
    capacity_operations: CapacityOperations | None = None,
    applied_by: str | None = None,
    reason: str | None = None,
    lock_held: bool = False,
) -> CapacityAdmissionDecision:
    """Admit a validated store, expanding the hot site only when needed.

    The configured capacity is the admission baseline. When the baseline is
    full and no ``capacity_operations`` journal is available, a
    ``CapacityAdmissionError`` is raised and the candidate remains pending
    with no hot-site mutation. When a journal is available, the store is
    expanded (never evicting) under the capacity mutation lock and admission
    is re-evaluated against the live elastic capacity. When ``lock_held`` is
    True, the caller already holds the capacity mutation lock, so the
    expansion runs under that lock instead of acquiring it again (the file
    lock is not reentrant).
    """

    decision = evaluate_capacity_admission(
        hot_site,
        configured_capacity=configured_capacity,
        required_slots=required_slots,
    )

    if decision.allowed:
        return decision

    if capacity_operations is None:
        raise CapacityAdmissionError(decision.reason)

    reviewer = (applied_by or "").strip()
    explanation = (reason or "").strip()

    if not reviewer:
        raise ValueError(
            "applied_by must not be empty when expanding."
        )
    if not explanation:
        raise ValueError(
            "reason must not be empty when expanding."
        )

    lock_context = (
        nullcontext()
        if lock_held
        else capacity_operations.mutation_lock(
            "capacity_expansion"
        )
    )

    with lock_context:
        before = int(
            hot_site.capacity_status()["current_capacity"]
        )
        expanded = hot_site.ensure_capacity_for(
            required_slots
        )
        capacity_operations.record(
            "capacity_expanded",
            {
                "configured_capacity": configured_capacity,
                "required_slots": required_slots,
                "capacity_before": before,
                "capacity_after": expanded,
                "applied_by": reviewer,
                "reason": explanation,
            },
        )

        effective = evaluate_effective_capacity_admission(
            hot_site,
            configured_capacity=configured_capacity,
        )

    if not effective.allowed:
        raise CapacityAdmissionError(
            "Hot-site capacity is still exhausted after "
            "expansion; the candidate remains pending."
        )

    return effective


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
