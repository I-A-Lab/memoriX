"""Read-only policy lifecycle contracts and planning for memoriX.

Part 24.1-24.5 audits the existing policy system, models versioned policy
records, inspects an optional registry without creating it, previews an AutoML
proposal, and compares it with the active policy. No approval, activation,
rollback, registry write, runtime mutation, cold-site access, or Titan loading
is performed here.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from memory.adaptive.policy_search import (
    MemoryPolicyCandidate,
    MemoryPolicyMetrics,
    MemoryPolicySearchResult,
)
from memory.adaptive.adaptive_routing_policy import AdaptiveRoutingPolicy
from memory.adaptive.retention_scoring import (
    RetentionScoringThresholds,
    RetentionScoringWeights,
)


class MemoryPolicyLifecycleStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ROLLED_BACK = "rolled_back"
    ARCHIVED = "archived"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _candidate_from_dict(payload: Mapping[str, Any]) -> MemoryPolicyCandidate:
    return MemoryPolicyCandidate(
        policy_id=str(payload.get("policy_id", "")).strip(),
        description=str(payload.get("description", "")),
        retention_weights=RetentionScoringWeights(
            **dict(payload.get("retention_weights", {}))
        ),
        retention_thresholds=RetentionScoringThresholds(
            **dict(payload.get("retention_thresholds", {}))
        ),
        routing_policy=AdaptiveRoutingPolicy(
            **dict(payload.get("routing_policy", {}))
        ),
    )


@dataclass(frozen=True, slots=True)
class MemoryPolicyLifecycleAudit:
    candidate_contract: str
    search_result_contract: str
    persistence_present: bool
    activation_present: bool
    observations: tuple[str, ...]
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryPolicyVersion:
    version_id: str
    policy: MemoryPolicyCandidate
    status: MemoryPolicyLifecycleStatus
    created_at: str
    created_by: str
    source: str
    parent_version_id: str | None = None
    metrics: MemoryPolicyMetrics | None = None

    def validate(self) -> None:
        if not self.version_id.strip():
            raise ValueError("version_id must be non-empty.")
        if not self.created_at.strip():
            raise ValueError("created_at must be non-empty.")
        if not self.created_by.strip():
            raise ValueError("created_by must be non-empty.")
        if not self.source.strip():
            raise ValueError("source must be non-empty.")
        self.policy.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "policy": self.policy.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "source": self.source,
            "parent_version_id": self.parent_version_id,
            "metrics": None if self.metrics is None else self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MemoryPolicyVersion":
        metrics_payload = payload.get("metrics")
        metrics = None
        if isinstance(metrics_payload, Mapping):
            metrics = MemoryPolicyMetrics(
                retention_accuracy=_finite(metrics_payload.get("retention_accuracy")),
                routing_accuracy=_finite(metrics_payload.get("routing_accuracy")),
                protected_memory_safety=_finite(metrics_payload.get("protected_memory_safety")),
                retention_efficiency=_finite(metrics_payload.get("retention_efficiency")),
                stability=_finite(metrics_payload.get("stability")),
                complexity_penalty=_finite(metrics_payload.get("complexity_penalty")),
                combined_score=_finite(metrics_payload.get("combined_score")),
            )
        result = cls(
            version_id=str(payload.get("version_id", "")),
            policy=_candidate_from_dict(dict(payload.get("policy", {}))),
            status=MemoryPolicyLifecycleStatus(str(payload.get("status", "proposed"))),
            created_at=str(payload.get("created_at", "")),
            created_by=str(payload.get("created_by", "unknown")),
            source=str(payload.get("source", "registry")),
            parent_version_id=(
                None if payload.get("parent_version_id") is None
                else str(payload.get("parent_version_id"))
            ),
            metrics=metrics,
        )
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class MemoryPolicyProposalPreview:
    proposal_id: str
    proposed_version: MemoryPolicyVersion
    active_version_id: str | None
    proposal_reasons: tuple[str, ...]
    policy_proposed: bool = False
    policy_approved: bool = False
    policy_rejected: bool = False
    policy_activated: bool = False
    policy_rolled_back: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["proposed_version"] = self.proposed_version.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class MemoryPolicyRegistrySnapshot:
    runtime_root: str
    versions_path: str
    state_path: str
    versions: tuple[MemoryPolicyVersion, ...]
    active_policy_version_id: str | None
    previous_policy_version_id: str | None
    pending_proposal_ids: tuple[str, ...]
    malformed_record_count: int
    registry_exists: bool
    observation_only: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    @property
    def active_version(self) -> MemoryPolicyVersion | None:
        return next(
            (item for item in self.versions if item.version_id == self.active_policy_version_id),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_root": self.runtime_root,
            "versions_path": self.versions_path,
            "state_path": self.state_path,
            "versions": [item.to_dict() for item in self.versions],
            "active_policy_version_id": self.active_policy_version_id,
            "previous_policy_version_id": self.previous_policy_version_id,
            "pending_proposal_ids": list(self.pending_proposal_ids),
            "malformed_record_count": self.malformed_record_count,
            "registry_exists": self.registry_exists,
            "observation_only": self.observation_only,
            "registry_modified": self.registry_modified,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
        }


@dataclass(frozen=True, slots=True)
class MemoryPolicyComparison:
    current_version_id: str | None
    proposed_version_id: str
    policy_changed: bool
    combined_score_delta: float | None
    retention_accuracy_delta: float | None
    routing_accuracy_delta: float | None
    protected_memory_safety_delta: float | None
    parameter_deltas: Mapping[str, float]
    advantages: tuple[str, ...]
    risks: tuple[str, ...]
    recommendation: str
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["parameter_deltas"] = dict(self.parameter_deltas)
        return payload


def audit_memory_policy_lifecycle() -> MemoryPolicyLifecycleAudit:
    return MemoryPolicyLifecycleAudit(
        candidate_contract="memory.adaptive.policy_search.MemoryPolicyCandidate",
        search_result_contract="memory.adaptive.policy_search.MemoryPolicySearchResult",
        persistence_present=False,
        activation_present=False,
        observations=(
            "policy_candidates_are_currently_ephemeral",
            "policy_search_is_deterministic_and_dry_run",
            "no_active_policy_registry_exists_in_parts_1_to_23",
            "no_policy_activation_or_rollback_exists_in_parts_1_to_23",
            "part_24_must_not_duplicate_retention_or_routing_contracts",
        ),
    )


def inspect_memory_policy_registry(runtime_root: str | Path) -> MemoryPolicyRegistrySnapshot:
    root = Path(runtime_root).expanduser().resolve()
    policies_dir = root / "policies"
    versions_path = policies_dir / "policy_versions.jsonl"
    state_path = policies_dir / "policy_state.json"
    versions: list[MemoryPolicyVersion] = []
    malformed = 0
    if versions_path.is_file():
        for raw_line in versions_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                payload = json.loads(raw_line)
                if not isinstance(payload, Mapping):
                    raise ValueError("version record must be an object")
                versions.append(MemoryPolicyVersion.from_dict(payload))
            except (ValueError, TypeError, json.JSONDecodeError):
                malformed += 1
    state: Mapping[str, Any] = {}
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, Mapping):
                state = loaded
            else:
                malformed += 1
        except (OSError, json.JSONDecodeError):
            malformed += 1
    pending = state.get("pending_proposal_ids", ())
    if not isinstance(pending, (list, tuple)):
        pending = ()
        malformed += 1
    return MemoryPolicyRegistrySnapshot(
        runtime_root=str(root),
        versions_path=str(versions_path),
        state_path=str(state_path),
        versions=tuple(versions),
        active_policy_version_id=(
            None if state.get("active_policy_version_id") is None
            else str(state.get("active_policy_version_id"))
        ),
        previous_policy_version_id=(
            None if state.get("previous_policy_version_id") is None
            else str(state.get("previous_policy_version_id"))
        ),
        pending_proposal_ids=tuple(str(item) for item in pending),
        malformed_record_count=malformed,
        registry_exists=versions_path.exists() or state_path.exists(),
    )


def preview_memory_policy_proposal(
    search_result: MemoryPolicySearchResult,
    *,
    proposal_id: str,
    created_by: str,
    active_version_id: str | None = None,
    created_at: str | None = None,
) -> MemoryPolicyProposalPreview:
    if not proposal_id.strip():
        raise ValueError("proposal_id must be non-empty.")
    version = MemoryPolicyVersion(
        version_id=proposal_id,
        policy=search_result.best_policy,
        status=MemoryPolicyLifecycleStatus.PROPOSED,
        created_at=created_at or _utc_now(),
        created_by=created_by,
        source="automl_policy_search",
        parent_version_id=active_version_id,
        metrics=search_result.trials[0].metrics,
    )
    version.validate()
    return MemoryPolicyProposalPreview(
        proposal_id=proposal_id,
        proposed_version=version,
        active_version_id=active_version_id,
        proposal_reasons=(
            "best_policy_from_deterministic_search",
            "manual_review_required",
            "proposal_does_not_approve_or_activate_policy",
        ),
    )


def compare_memory_policy_versions(
    current: MemoryPolicyVersion | None,
    proposed: MemoryPolicyVersion,
) -> MemoryPolicyComparison:
    proposed.validate()
    current_policy = current.policy if current is not None else None
    deltas: dict[str, float] = {}
    groups = (
        ("retention_weights", proposed.policy.retention_weights,
         None if current_policy is None else current_policy.retention_weights),
        ("retention_thresholds", proposed.policy.retention_thresholds,
         None if current_policy is None else current_policy.retention_thresholds),
        ("routing_policy", proposed.policy.routing_policy,
         None if current_policy is None else current_policy.routing_policy),
    )
    for prefix, proposed_group, current_group in groups:
        proposed_values = asdict(proposed_group)
        current_values = {} if current_group is None else asdict(current_group)
        for key, value in proposed_values.items():
            if isinstance(value, bool):
                continue
            baseline = current_values.get(key, value)
            deltas[f"{prefix}.{key}"] = _finite(value) - _finite(baseline)

    def metric_delta(name: str) -> float | None:
        if current is None or current.metrics is None or proposed.metrics is None:
            return None
        return _finite(getattr(proposed.metrics, name)) - _finite(
            getattr(current.metrics, name)
        )

    score_delta = metric_delta("combined_score")
    protected_delta = metric_delta("protected_memory_safety")
    advantages: list[str] = []
    risks: list[str] = []
    if score_delta is not None and score_delta > 0:
        advantages.append("combined_score_improves")
    if metric_delta("retention_accuracy") is not None and metric_delta("retention_accuracy") > 0:
        advantages.append("retention_accuracy_improves")
    if metric_delta("routing_accuracy") is not None and metric_delta("routing_accuracy") > 0:
        advantages.append("routing_accuracy_improves")
    if protected_delta is not None and protected_delta < 0:
        risks.append("protected_memory_safety_decreases")
    if any(abs(value) >= 0.15 for value in deltas.values()):
        risks.append("large_parameter_change")
    policy_changed = current_policy is None or proposed.policy.to_dict() != current_policy.to_dict()
    return MemoryPolicyComparison(
        current_version_id=None if current is None else current.version_id,
        proposed_version_id=proposed.version_id,
        policy_changed=policy_changed,
        combined_score_delta=score_delta,
        retention_accuracy_delta=metric_delta("retention_accuracy"),
        routing_accuracy_delta=metric_delta("routing_accuracy"),
        protected_memory_safety_delta=protected_delta,
        parameter_deltas=deltas,
        advantages=tuple(advantages),
        risks=tuple(risks),
        recommendation="manual_review_required",
    )

@dataclass(frozen=True, slots=True)
class MemoryPolicyLifecycleResult:
    action: str
    ok: bool
    message: str
    version: MemoryPolicyVersion | None = None
    active_policy_version_id: str | None = None
    previous_policy_version_id: str | None = None
    policy_proposed: bool = False
    policy_approved: bool = False
    policy_rejected: bool = False
    policy_activated: bool = False
    policy_rolled_back: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ok": self.ok,
            "message": self.message,
            "version": None if self.version is None else self.version.to_dict(),
            "active_policy_version_id": self.active_policy_version_id,
            "previous_policy_version_id": self.previous_policy_version_id,
            "policy_proposed": self.policy_proposed,
            "policy_approved": self.policy_approved,
            "policy_rejected": self.policy_rejected,
            "policy_activated": self.policy_activated,
            "policy_rolled_back": self.policy_rolled_back,
            "registry_modified": self.registry_modified,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
        }


@dataclass(frozen=True, slots=True)
class MemoryPolicyActivationPlan:
    version_id: str
    allowed: bool
    blocking_reasons: tuple[str, ...]
    operations: tuple[str, ...]
    active_policy_version_id: str | None
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryPolicyRollbackPlan:
    current_version_id: str | None
    target_version_id: str | None
    allowed: bool
    blocking_reasons: tuple[str, ...]
    operations: tuple[str, ...]
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _registry_paths(runtime_root: str | Path) -> tuple[Path, Path, Path]:
    root = Path(runtime_root).expanduser().resolve()
    directory = root / "policies"
    return directory, directory / "policy_versions.jsonl", directory / "policy_state.json"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _load_versions_for_write(path: Path) -> list[MemoryPolicyVersion]:
    if not path.is_file():
        return []
    versions: list[MemoryPolicyVersion] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            payload = json.loads(line)
            if not isinstance(payload, Mapping):
                raise ValueError("policy registry record must be an object")
            versions.append(MemoryPolicyVersion.from_dict(payload))
    return versions


def _load_state_for_write(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "active_policy_version_id": None,
            "previous_policy_version_id": None,
            "pending_proposal_ids": [],
            "updated_at": _utc_now(),
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy registry state must be an object")
    pending = payload.get("pending_proposal_ids", [])
    if not isinstance(pending, list):
        raise ValueError("pending_proposal_ids must be an array")
    return payload


def _persist_registry(
    versions_path: Path,
    state_path: Path,
    versions: list[MemoryPolicyVersion],
    state: Mapping[str, Any],
) -> None:
    versions_text = "".join(
        json.dumps(version.to_dict(), sort_keys=True) + "\n"
        for version in versions
    )
    _atomic_write(versions_path, versions_text)
    _atomic_write(state_path, json.dumps(dict(state), indent=2, sort_keys=True) + "\n")


def propose_memory_policy(
    runtime_root: str | Path,
    search_result: MemoryPolicySearchResult,
    *,
    proposal_id: str,
    created_by: str,
    created_at: str | None = None,
) -> MemoryPolicyLifecycleResult:
    directory, versions_path, state_path = _registry_paths(runtime_root)
    versions = _load_versions_for_write(versions_path)
    if any(item.version_id == proposal_id for item in versions):
        return MemoryPolicyLifecycleResult("propose", False, "proposal_already_exists")
    state = _load_state_for_write(state_path)
    preview = preview_memory_policy_proposal(
        search_result,
        proposal_id=proposal_id,
        created_by=created_by,
        active_version_id=state.get("active_policy_version_id"),
        created_at=created_at,
    )
    versions.append(preview.proposed_version)
    pending = [str(item) for item in state.get("pending_proposal_ids", [])]
    pending.append(proposal_id)
    state.update({"pending_proposal_ids": sorted(set(pending)), "updated_at": _utc_now()})
    directory.mkdir(parents=True, exist_ok=True)
    _persist_registry(versions_path, state_path, versions, state)
    return MemoryPolicyLifecycleResult(
        "propose", True, "policy_proposed", preview.proposed_version,
        active_policy_version_id=state.get("active_policy_version_id"),
        previous_policy_version_id=state.get("previous_policy_version_id"),
        policy_proposed=True, registry_modified=True,
    )


def review_memory_policy(
    runtime_root: str | Path,
    *,
    version_id: str,
    approved: bool,
    reviewed_by: str,
    reason: str,
    validation_id: str,
) -> MemoryPolicyLifecycleResult:
    if not reviewed_by.strip() or not reason.strip() or not validation_id.strip():
        raise ValueError("reviewed_by, reason and validation_id must be non-empty")
    _, versions_path, state_path = _registry_paths(runtime_root)
    versions = _load_versions_for_write(versions_path)
    state = _load_state_for_write(state_path)
    index = next((i for i, item in enumerate(versions) if item.version_id == version_id), None)
    if index is None:
        return MemoryPolicyLifecycleResult("approve" if approved else "reject", False, "policy_not_found")
    current = versions[index]
    if current.status is not MemoryPolicyLifecycleStatus.PROPOSED:
        return MemoryPolicyLifecycleResult("approve" if approved else "reject", False, "policy_not_pending", current)
    status = MemoryPolicyLifecycleStatus.APPROVED if approved else MemoryPolicyLifecycleStatus.REJECTED
    updated = MemoryPolicyVersion(
        version_id=current.version_id, policy=current.policy, status=status,
        created_at=current.created_at, created_by=current.created_by,
        source=current.source, parent_version_id=current.parent_version_id,
        metrics=current.metrics,
    )
    versions[index] = updated
    pending = [item for item in state.get("pending_proposal_ids", []) if str(item) != version_id]
    state.update({"pending_proposal_ids": pending, "updated_at": _utc_now(), "last_validation_id": validation_id, "last_reviewed_by": reviewed_by, "last_review_reason": reason})
    _persist_registry(versions_path, state_path, versions, state)
    return MemoryPolicyLifecycleResult(
        "approve" if approved else "reject", True,
        "policy_approved" if approved else "policy_rejected", updated,
        active_policy_version_id=state.get("active_policy_version_id"),
        previous_policy_version_id=state.get("previous_policy_version_id"),
        policy_approved=approved, policy_rejected=not approved,
        registry_modified=True,
    )


def plan_memory_policy_activation(runtime_root: str | Path, version_id: str) -> MemoryPolicyActivationPlan:
    snapshot = inspect_memory_policy_registry(runtime_root)
    version = next((item for item in snapshot.versions if item.version_id == version_id), None)
    blockers: list[str] = []
    if version is None: blockers.append("policy_not_found")
    elif version.status is not MemoryPolicyLifecycleStatus.APPROVED: blockers.append("policy_not_approved")
    if snapshot.malformed_record_count: blockers.append("registry_contains_malformed_records")
    return MemoryPolicyActivationPlan(
        version_id=version_id, allowed=not blockers, blocking_reasons=tuple(blockers),
        operations=("verify_registry", "verify_human_approval", "save_previous_active_version", "activate_registry_version", "verify_registry_state"),
        active_policy_version_id=snapshot.active_policy_version_id,
    )


def activate_memory_policy(
    runtime_root: str | Path,
    *,
    version_id: str,
    activated_by: str,
    reason: str,
    validation_id: str,
) -> MemoryPolicyLifecycleResult:
    if not activated_by.strip() or not reason.strip() or not validation_id.strip():
        raise ValueError("activated_by, reason and validation_id must be non-empty")
    plan = plan_memory_policy_activation(runtime_root, version_id)
    if not plan.allowed:
        return MemoryPolicyLifecycleResult("activate", False, ",".join(plan.blocking_reasons))
    _, versions_path, state_path = _registry_paths(runtime_root)
    versions = _load_versions_for_write(versions_path)
    state = _load_state_for_write(state_path)
    old_active = state.get("active_policy_version_id")
    updated_versions: list[MemoryPolicyVersion] = []
    activated_version: MemoryPolicyVersion | None = None
    for item in versions:
        status = item.status
        if item.version_id == version_id:
            status = MemoryPolicyLifecycleStatus.ACTIVE
        elif item.version_id == old_active and item.status is MemoryPolicyLifecycleStatus.ACTIVE:
            status = MemoryPolicyLifecycleStatus.SUPERSEDED
        updated = MemoryPolicyVersion(item.version_id, item.policy, status, item.created_at, item.created_by, item.source, item.parent_version_id, item.metrics)
        updated_versions.append(updated)
        if item.version_id == version_id: activated_version = updated
    state.update({"previous_policy_version_id": old_active, "active_policy_version_id": version_id, "updated_at": _utc_now(), "last_validation_id": validation_id, "last_activated_by": activated_by, "last_activation_reason": reason})
    _persist_registry(versions_path, state_path, updated_versions, state)
    return MemoryPolicyLifecycleResult(
        "activate", True, "policy_activated", activated_version,
        active_policy_version_id=version_id, previous_policy_version_id=old_active,
        policy_activated=True, registry_modified=True,
    )


def plan_memory_policy_rollback(runtime_root: str | Path) -> MemoryPolicyRollbackPlan:
    snapshot = inspect_memory_policy_registry(runtime_root)
    blockers: list[str] = []
    if snapshot.active_policy_version_id is None: blockers.append("no_active_policy")
    if snapshot.previous_policy_version_id is None: blockers.append("no_previous_policy")
    previous = next((item for item in snapshot.versions if item.version_id == snapshot.previous_policy_version_id), None)
    if snapshot.previous_policy_version_id is not None and previous is None: blockers.append("previous_policy_not_found")
    return MemoryPolicyRollbackPlan(
        current_version_id=snapshot.active_policy_version_id,
        target_version_id=snapshot.previous_policy_version_id,
        allowed=not blockers, blocking_reasons=tuple(blockers),
        operations=("verify_registry", "verify_previous_policy", "mark_current_rolled_back", "restore_previous_policy", "verify_registry_state"),
    )


def rollback_memory_policy(
    runtime_root: str | Path,
    *,
    rolled_back_by: str,
    reason: str,
    validation_id: str,
) -> MemoryPolicyLifecycleResult:
    if not rolled_back_by.strip() or not reason.strip() or not validation_id.strip():
        raise ValueError("rolled_back_by, reason and validation_id must be non-empty")
    plan = plan_memory_policy_rollback(runtime_root)
    if not plan.allowed or plan.target_version_id is None:
        return MemoryPolicyLifecycleResult("rollback", False, ",".join(plan.blocking_reasons))
    _, versions_path, state_path = _registry_paths(runtime_root)
    versions = _load_versions_for_write(versions_path)
    state = _load_state_for_write(state_path)
    restored: MemoryPolicyVersion | None = None
    updated_versions: list[MemoryPolicyVersion] = []
    for item in versions:
        status = item.status
        if item.version_id == plan.current_version_id:
            status = MemoryPolicyLifecycleStatus.ROLLED_BACK
        elif item.version_id == plan.target_version_id:
            status = MemoryPolicyLifecycleStatus.ACTIVE
        updated = MemoryPolicyVersion(item.version_id, item.policy, status, item.created_at, item.created_by, item.source, item.parent_version_id, item.metrics)
        updated_versions.append(updated)
        if item.version_id == plan.target_version_id: restored = updated
    state.update({"active_policy_version_id": plan.target_version_id, "previous_policy_version_id": plan.current_version_id, "updated_at": _utc_now(), "last_validation_id": validation_id, "last_rolled_back_by": rolled_back_by, "last_rollback_reason": reason})
    _persist_registry(versions_path, state_path, updated_versions, state)
    return MemoryPolicyLifecycleResult(
        "rollback", True, "policy_rolled_back", restored,
        active_policy_version_id=plan.target_version_id,
        previous_policy_version_id=plan.current_version_id,
        policy_rolled_back=True, registry_modified=True,
    )
