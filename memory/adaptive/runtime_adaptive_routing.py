"""Read-only runtime adapter for adaptive routing plans."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from memory.adaptive.adaptive_routing_policy import (
    AdaptiveRoutingInput,
    AdaptiveRoutingPlan,
    RoutingPruningCandidate,
    plan_adaptive_routing,
)
from memory.adaptive.runtime_retention_scoring import (
    inspect_runtime_retention_ranking,
)
from memory.adaptive.runtime_capacity import inspect_runtime_capacity


@dataclass(frozen=True, slots=True)
class RuntimeAdaptiveRoutingReport:
    status: str
    runtime_root: str
    simulated: bool
    target_id: str
    plan: AdaptiveRoutingPlan
    retention_assessments_considered: int
    dry_run: bool = True
    applied: bool = False
    candidate_validated: bool = False
    pruning_executed: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plan"] = self.plan.to_dict()
        return payload


def inspect_runtime_adaptive_routing(
    *,
    runtime_root: str | Path,
    target_id: str,
    retention_score: float = 0.5,
    importance: float = 0.5,
    confidence: float = 0.5,
    surprise: float = 0.0,
    protected: bool = False,
    pinned: bool = False,
    human_validated: bool = True,
    required_slots: int = 1,
    configured_capacity: int = 50_000,
    assessment_limit: int = 100,
    simulated_memory_count: int | None = None,
) -> RuntimeAdaptiveRoutingReport:
    target = target_id.strip()
    if not target:
        raise ValueError("target_id must be non-empty.")
    if assessment_limit < 0:
        raise ValueError("assessment_limit must be non-negative.")

    capacity = inspect_runtime_capacity(
        runtime_root=runtime_root,
        configured_capacity=configured_capacity,
        simulated_active_items=simulated_memory_count,
    )
    ranking = inspect_runtime_retention_ranking(
        runtime_root=runtime_root,
        assessment_limit=assessment_limit,
        simulated_memory_count=simulated_memory_count,
    )
    pruning_candidates = tuple(
        RoutingPruningCandidate(
            memory_id=item.memory_id,
            retention_score=item.retention_score,
            active=True,
            protected=item.protected,
            pinned=bool(item.protection_reasons and "pinned" in item.protection_reasons),
            human_validated=True,
        )
        for item in ranking.ranking.assessments
    )
    source = AdaptiveRoutingInput(
        target_id=target,
        retention_score=retention_score,
        importance=importance,
        confidence=confidence,
        surprise=surprise,
        protected=protected,
        pinned=pinned,
        human_validated=human_validated,
        configured_capacity=configured_capacity,
        active_memories=capacity.active_memories,
        required_slots=required_slots,
        pruning_candidates=pruning_candidates,
    )
    plan = plan_adaptive_routing(source)
    return RuntimeAdaptiveRoutingReport(
        status="ok",
        runtime_root=str(Path(runtime_root)),
        simulated=simulated_memory_count is not None,
        target_id=target,
        plan=plan,
        retention_assessments_considered=len(pruning_candidates),
    )
