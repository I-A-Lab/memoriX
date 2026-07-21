"""Deterministic, action-free adaptive routing decisions.

The policy combines explicit candidate or memory measurements with hot-site
capacity and retention information. It only returns explainable dry-run plans.
It never validates a candidate, prunes memory, writes runtime files, reads the
cold site, or loads Titan neural weights.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from memory.adaptive.contracts import PressureLevel, utc_now_iso
from memory.adaptive.runtime_capacity import classify_runtime_pressure


def _clamp_unit(value: float, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default

    if not math.isfinite(number):
        number = default

    return max(0.0, min(1.0, number))


class AdaptiveRoutingDecisionType(str, Enum):
    """Supported action-free routing outcomes."""

    ADMIT = "admit"
    ADMIT_AFTER_PRUNING = "admit_after_pruning"
    KEEP = "keep"
    PROTECT = "protect"
    DEFER = "defer"
    REJECT_SAFELY = "reject_safely"
    REVIEW_FOR_SOFT_PRUNING = "review_for_soft_pruning"


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingPolicy:
    """Thresholds used by the deterministic routing planner."""

    minimum_admission_score: float = 0.45
    high_priority_score: float = 0.65
    soft_pruning_score: float = 0.25
    maximum_pruning_items: int = 100

    def validate(self) -> None:
        values = (
            self.minimum_admission_score,
            self.high_priority_score,
            self.soft_pruning_score,
        )
        if any(
            not math.isfinite(value)
            or value < 0.0
            or value > 1.0
            for value in values
        ):
            raise ValueError(
                "Routing thresholds must be finite values between 0 and 1."
            )

        if not (
            self.soft_pruning_score
            <= self.minimum_admission_score
            <= self.high_priority_score
        ):
            raise ValueError(
                "Routing thresholds must satisfy "
                "soft_pruning <= minimum_admission <= high_priority."
            )

        if self.maximum_pruning_items <= 0:
            raise ValueError(
                "maximum_pruning_items must be strictly positive."
            )


@dataclass(frozen=True, slots=True)
class RoutingPruningCandidate:
    """One hot memory that may appear in a dry-run pruning proposal."""

    memory_id: str
    retention_score: float
    active: bool = True
    protected: bool = False
    pinned: bool = False
    human_validated: bool = True

    def validate(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must be a non-empty string.")


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingInput:
    """Explicit data used for one routing decision."""

    target_id: str
    target_kind: str = "candidate"
    retention_score: float = 0.5
    importance: float = 0.5
    confidence: float = 0.5
    surprise: float = 0.0
    protected: bool = False
    pinned: bool = False
    human_validated: bool = True
    configured_capacity: int = 1
    active_memories: int = 0
    required_slots: int = 1
    pruning_candidates: Sequence[RoutingPruningCandidate] = ()
    metadata: Mapping[str, Any] | None = None
    observed_at: str | None = None

    def validate(self) -> None:
        if not self.target_id.strip():
            raise ValueError("target_id must be a non-empty string.")

        if self.target_kind not in {"candidate", "memory"}:
            raise ValueError(
                "target_kind must be either 'candidate' or 'memory'."
            )

        if self.configured_capacity <= 0:
            raise ValueError(
                "configured_capacity must be strictly positive."
            )

        if self.active_memories < 0:
            raise ValueError(
                "active_memories must be non-negative."
            )

        if self.required_slots <= 0:
            raise ValueError(
                "required_slots must be strictly positive."
            )

        for candidate in self.pruning_candidates:
            candidate.validate()


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingContext:
    """Normalized context used to explain one routing evaluation."""

    retention_score: float
    pressure_score: float
    importance: float
    confidence: float
    surprise: float
    configured_capacity: int
    active_memories: int
    required_slots: int
    available_slots: int
    usage_ratio: float
    capacity_level: PressureLevel
    protected: bool
    protection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capacity_level"] = self.capacity_level.value
        payload["protection_reasons"] = list(
            self.protection_reasons
        )
        return payload


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingDecision:
    """One explainable and non-applied routing decision."""

    decision_id: str
    target_id: str
    target_kind: str
    decision: AdaptiveRoutingDecisionType
    allowed: bool
    requires_permission: bool
    reasons: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    recommended_next_step: str
    context: AdaptiveRoutingContext
    observed_at: str
    dry_run: bool = True
    applied: bool = False
    candidate_validated: bool = False
    pruning_executed: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "target_id": self.target_id,
            "target_kind": self.target_kind,
            "decision": self.decision.value,
            "allowed": self.allowed,
            "requires_permission": self.requires_permission,
            "reasons": list(self.reasons),
            "blocking_reasons": list(self.blocking_reasons),
            "recommended_next_step": self.recommended_next_step,
            "context": self.context.to_dict(),
            "observed_at": self.observed_at,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "candidate_validated": self.candidate_validated,
            "pruning_executed": self.pruning_executed,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True, slots=True)
class AdaptiveRoutingPlan:
    """Ordered dry-run plan accompanying one routing decision."""

    plan_id: str
    decision: AdaptiveRoutingDecision
    pruning_memory_ids: tuple[str, ...]
    required_slots: int
    slots_to_release: int
    capacity_before: int
    capacity_after_estimate: int
    operation_order: tuple[str, ...]
    fallback: str
    created_at: str
    dry_run: bool = True
    applied: bool = False
    candidate_validated: bool = False
    pruning_executed: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "decision": self.decision.to_dict(),
            "pruning_memory_ids": list(self.pruning_memory_ids),
            "required_slots": self.required_slots,
            "slots_to_release": self.slots_to_release,
            "capacity_before": self.capacity_before,
            "capacity_after_estimate": self.capacity_after_estimate,
            "operation_order": list(self.operation_order),
            "fallback": self.fallback,
            "created_at": self.created_at,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "candidate_validated": self.candidate_validated,
            "pruning_executed": self.pruning_executed,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
            "schema_version": self.schema_version,
        }


def _protection_reasons(
    source: AdaptiveRoutingInput,
) -> tuple[str, ...]:
    return tuple(
        reason
        for reason, enabled in (
            ("explicitly_protected", source.protected),
            ("pinned", source.pinned),
            ("not_human_validated", not source.human_validated),
        )
        if enabled
    )


def _routing_context(
    source: AdaptiveRoutingInput,
) -> AdaptiveRoutingContext:
    retention = _clamp_unit(
        source.retention_score,
        default=0.5,
    )
    available_slots = max(
        0,
        source.configured_capacity
        - source.active_memories,
    )

    return AdaptiveRoutingContext(
        retention_score=retention,
        pressure_score=1.0 - retention,
        importance=_clamp_unit(
            source.importance,
            default=0.5,
        ),
        confidence=_clamp_unit(
            source.confidence,
            default=0.5,
        ),
        surprise=_clamp_unit(source.surprise),
        configured_capacity=source.configured_capacity,
        active_memories=source.active_memories,
        required_slots=source.required_slots,
        available_slots=available_slots,
        usage_ratio=(
            source.active_memories
            / source.configured_capacity
        ),
        capacity_level=classify_runtime_pressure(
            source.active_memories,
            source.configured_capacity,
        ),
        protected=bool(_protection_reasons(source)),
        protection_reasons=_protection_reasons(source),
    )


def _eligible_pruning_candidates(
    source: AdaptiveRoutingInput,
    *,
    target_score: float,
    policy: AdaptiveRoutingPolicy,
) -> tuple[RoutingPruningCandidate, ...]:
    eligible = (
        candidate
        for candidate in source.pruning_candidates
        if candidate.active
        and not candidate.protected
        and not candidate.pinned
        and candidate.human_validated
        and _clamp_unit(candidate.retention_score)
        <= policy.soft_pruning_score
        and _clamp_unit(candidate.retention_score)
        < target_score
    )

    return tuple(
        sorted(
            eligible,
            key=lambda candidate: (
                _clamp_unit(candidate.retention_score),
                candidate.memory_id,
            ),
        )[: policy.maximum_pruning_items]
    )


def decide_adaptive_routing(
    source: AdaptiveRoutingInput,
    *,
    policy: AdaptiveRoutingPolicy | None = None,
    decision_id: str | None = None,
) -> AdaptiveRoutingDecision:
    """Return one deterministic routing outcome without applying it."""

    source.validate()
    resolved_policy = policy or AdaptiveRoutingPolicy()
    resolved_policy.validate()
    context = _routing_context(source)

    reasons: list[str] = []
    blockers: list[str] = []

    if context.protected:
        reasons.extend(context.protection_reasons)

    if context.retention_score >= resolved_policy.high_priority_score:
        reasons.append("high_retention_score")
    elif (
        context.retention_score
        >= resolved_policy.minimum_admission_score
    ):
        reasons.append("admissible_retention_score")
    else:
        blockers.append("retention_score_below_admission_threshold")

    if context.capacity_level is PressureLevel.CRITICAL:
        reasons.append("hot_site_capacity_critical")
    elif context.capacity_level is PressureLevel.HIGH:
        reasons.append("hot_site_capacity_high")
    elif context.capacity_level is PressureLevel.WATCH:
        reasons.append("hot_site_capacity_watch")
    else:
        reasons.append("hot_site_capacity_stable")

    enough_capacity = (
        context.available_slots >= source.required_slots
    )

    if source.target_kind == "memory":
        if context.protected:
            decision = AdaptiveRoutingDecisionType.PROTECT
            allowed = True
            requires_permission = False
            next_step = "keep_memory_protected"
        elif (
            context.retention_score
            < resolved_policy.soft_pruning_score
        ):
            decision = (
                AdaptiveRoutingDecisionType
                .REVIEW_FOR_SOFT_PRUNING
            )
            allowed = False
            requires_permission = True
            next_step = "request_soft_pruning_review"
        else:
            decision = AdaptiveRoutingDecisionType.KEEP
            allowed = True
            requires_permission = False
            next_step = "keep_memory"
    elif not source.human_validated:
        decision = AdaptiveRoutingDecisionType.DEFER
        allowed = False
        requires_permission = False
        blockers.append("candidate_not_human_validated")
        next_step = "request_manual_candidate_validation"
    elif (
        context.retention_score
        < resolved_policy.minimum_admission_score
    ):
        decision = AdaptiveRoutingDecisionType.DEFER
        allowed = False
        requires_permission = False
        next_step = "keep_candidate_pending"
    elif enough_capacity:
        decision = (
            AdaptiveRoutingDecisionType.PROTECT
            if context.protected
            else AdaptiveRoutingDecisionType.ADMIT
        )
        allowed = True
        requires_permission = False
        next_step = (
            "admit_and_mark_protected"
            if context.protected
            else "admit_candidate"
        )
    else:
        eligible = _eligible_pruning_candidates(
            source,
            target_score=context.retention_score,
            policy=resolved_policy,
        )
        slots_needed = max(
            0,
            source.required_slots
            - context.available_slots,
        )

        if len(eligible) >= slots_needed:
            decision = (
                AdaptiveRoutingDecisionType
                .ADMIT_AFTER_PRUNING
            )
            allowed = False
            requires_permission = True
            reasons.append("soft_pruning_can_release_capacity")
            next_step = "request_permission_for_soft_pruning"
        else:
            decision = AdaptiveRoutingDecisionType.REJECT_SAFELY
            allowed = False
            requires_permission = False
            blockers.extend(
                (
                    "insufficient_capacity",
                    "insufficient_prunable_memories",
                )
            )
            next_step = "preserve_candidate_without_admission"

    return AdaptiveRoutingDecision(
        decision_id=(
            decision_id
            or f"routing_decision_{uuid.uuid4().hex}"
        ),
        target_id=source.target_id,
        target_kind=source.target_kind,
        decision=decision,
        allowed=allowed,
        requires_permission=requires_permission,
        reasons=tuple(dict.fromkeys(reasons)),
        blocking_reasons=tuple(dict.fromkeys(blockers)),
        recommended_next_step=next_step,
        context=context,
        observed_at=source.observed_at or utc_now_iso(),
    )


def plan_adaptive_routing(
    source: AdaptiveRoutingInput,
    *,
    policy: AdaptiveRoutingPolicy | None = None,
    decision_id: str | None = None,
    plan_id: str | None = None,
) -> AdaptiveRoutingPlan:
    """Build an ordered and non-applied plan for one routing decision."""

    resolved_policy = policy or AdaptiveRoutingPolicy()
    decision = decide_adaptive_routing(
        source,
        policy=resolved_policy,
        decision_id=decision_id,
    )
    context = decision.context
    slots_needed = max(
        0,
        source.required_slots - context.available_slots,
    )
    pruning_memory_ids: tuple[str, ...] = ()

    if (
        decision.decision
        is AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING
    ):
        eligible = _eligible_pruning_candidates(
            source,
            target_score=context.retention_score,
            policy=resolved_policy,
        )
        pruning_memory_ids = tuple(
            candidate.memory_id
            for candidate in eligible[:slots_needed]
        )

    if decision.decision is AdaptiveRoutingDecisionType.ADMIT:
        operation_order = (
            "verify_candidate_validation",
            "verify_capacity",
            "admit_candidate",
            "verify_hot_site_state",
        )
        fallback = "preserve_candidate_pending"
    elif decision.decision is AdaptiveRoutingDecisionType.PROTECT:
        operation_order = (
            "verify_protection_contract",
            "verify_capacity",
            "keep_or_admit_protected_target",
        )
        fallback = "preserve_protected_target"
    elif (
        decision.decision
        is AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING
    ):
        operation_order = (
            "verify_candidate_validation",
            "request_soft_pruning_permission",
            "recheck_capacity",
            "execute_separately_authorized_soft_pruning",
            "recheck_capacity",
            "admit_candidate",
            "verify_hot_site_state",
        )
        fallback = "preserve_candidate_pending"
    elif (
        decision.decision
        is AdaptiveRoutingDecisionType.REVIEW_FOR_SOFT_PRUNING
    ):
        operation_order = (
            "request_soft_pruning_review",
            "preserve_memory_until_authorized",
        )
        fallback = "keep_memory"
    else:
        operation_order = (
            "preserve_target",
            "record_blocking_reasons",
        )
        fallback = "preserve_target_without_mutation"

    released = len(pruning_memory_ids)
    capacity_after = (
        context.active_memories
        - released
        + (
            source.required_slots
            if decision.decision
            in {
                AdaptiveRoutingDecisionType.ADMIT,
                AdaptiveRoutingDecisionType.PROTECT,
                AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING,
            }
            and source.target_kind == "candidate"
            else 0
        )
    )

    return AdaptiveRoutingPlan(
        plan_id=plan_id or f"routing_plan_{uuid.uuid4().hex}",
        decision=decision,
        pruning_memory_ids=pruning_memory_ids,
        required_slots=source.required_slots,
        slots_to_release=slots_needed,
        capacity_before=context.active_memories,
        capacity_after_estimate=capacity_after,
        operation_order=operation_order,
        fallback=fallback,
        created_at=source.observed_at or utc_now_iso(),
    )
