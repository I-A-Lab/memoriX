"""Resolve the currently active adaptive policy from the runtime registry."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from memory.adaptive.adaptive_routing_policy import AdaptiveRoutingPolicy
from memory.adaptive.policy_lifecycle import inspect_memory_policy_registry
from memory.adaptive.retention_scoring import RetentionScoringThresholds, RetentionScoringWeights

@dataclass(frozen=True, slots=True)
class ActiveMemoryPolicy:
    version_id: str | None
    retention_weights: RetentionScoringWeights
    retention_thresholds: RetentionScoringThresholds
    routing_policy: AdaptiveRoutingPolicy
    registry_used: bool


def load_active_memory_policy(runtime_root: str | Path) -> ActiveMemoryPolicy:
    snapshot = inspect_memory_policy_registry(runtime_root)
    active = next(
        (version for version in snapshot.versions if version.version_id == snapshot.active_policy_version_id),
        None,
    )
    if active is None:
        return ActiveMemoryPolicy(
            version_id=None,
            retention_weights=RetentionScoringWeights(),
            retention_thresholds=RetentionScoringThresholds(),
            routing_policy=AdaptiveRoutingPolicy(),
            registry_used=False,
        )
    return ActiveMemoryPolicy(
        version_id=active.version_id,
        retention_weights=active.policy.retention_weights,
        retention_thresholds=active.policy.retention_thresholds,
        routing_policy=active.policy.routing_policy,
        registry_used=True,
    )
