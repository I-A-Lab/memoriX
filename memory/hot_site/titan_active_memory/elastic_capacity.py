"""Elastic global Hot-Titan capacity management.

Phase 2A5 introduces a single elastic global Hot-Titan capacity: the active
hot site starts at a configured baseline and temporarily expands (never
evicts) when validated memories would exceed it. Expansion is a hot-site-only
operation; the cold archive is never read or mutated here.

The nightly capacity maintenance path runs only while the hot site is
expanded:

    prune -> consistency gate -> compact -> shrink

The ENFORCED Phase 2A5 contract:

- ``run_nightly_capacity_maintenance(hot_site, *, policy=None,
  capacity_operations, run_reference, cold_archive_path=None, log_path=None)``
  returns a ``NightlyCapacityMaintenanceResult`` whose ``to_dict()`` exposes
  EXACTLY 12 keys in order: capacity_before, capacity_after, active_before,
  active_after, automatic_soft_forgets, compaction_attempted,
  compaction_applied, shrink_attempted, shrink_applied,
  shrink_skipped_reason, consistency_ok, cold_site_modified.
- The nightly observes pressure with
  ``weights=PressureWeights(usage_ratio=1.0, momentum=0.0, entropy=0.0,
  surprise=0.0, persistence=0.0)`` so that ``memory_pressure == active /
  current_capacity``. The default ``SoftPruningPolicy.minimum_pressure``
  (0.70) is therefore reachable at >= 70% usage under the default policy and
  the automatic soft-pruning branch is never a dead canary.
- Automatic soft-forgets are applied by the fixed reviewer constant
  ``NIGHTLY_CAPACITY_REVIEWER == "memorix_nightly_capacity"`` and the forget
  reason contains the run reference. ``ElasticCapacityPolicy.
  max_automatic_deactivations`` is wired through ``apply_soft_pruning_plan``.
- Restoration to the baseline happens only when
  ``active_after <= floor(baseline * headroom_ratio)`` (headroom ratio 0.80
  by default) AND the consistency gate passed.
- When the hot site is not expanded the run is a no-op result with every
  counter 0, ``capacity_after == capacity_before``, ``consistency_ok`` False,
  ``shrink_attempted`` False and ``shrink_skipped_reason`` ""; no mutation
  lock is acquired and no capacity event is recorded.
- The cold archive is fingerprinted before and after the action path; any
  difference raises ``RuntimeError`` and the run never reports
  ``cold_site_modified`` as False while the archive changed.

This module never imports torch and never performs storage mutations itself.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

from memory.adaptive.contracts import (
    HotMemoryPruningInput,
    PressureObservationInput,
    PressureWeights,
    utc_now_iso,
)
from memory.adaptive.pressure import observe_memory_pressure
from memory.adaptive.pruning import plan_soft_pruning

if TYPE_CHECKING:
    from memory.gateway.capacity_operations import CapacityOperations
    from memory.hot_site.titan_active_memory.hot_site import HotSiteTitanMemory
    from memory.data import ValidatedMemory

HOT_SITE_SCOPE = "hot_site"
DEFAULT_CAPACITY_MINIMUM_GROWTH = 10
DEFAULT_CAPACITY_GROWTH_FACTOR = 1.25
DEFAULT_BASELINE_HEADROOM_RATIO = 0.80
DEFAULT_MAX_AUTOMATIC_DEACTIVATIONS = 200
NIGHTLY_CAPACITY_REVIEWER = "memorix_nightly_capacity"

__all__ = [
    "HOT_SITE_SCOPE",
    "DEFAULT_CAPACITY_MINIMUM_GROWTH",
    "DEFAULT_CAPACITY_GROWTH_FACTOR",
    "DEFAULT_BASELINE_HEADROOM_RATIO",
    "DEFAULT_MAX_AUTOMATIC_DEACTIVATIONS",
    "NIGHTLY_CAPACITY_REVIEWER",
    "ElasticCapacityPolicy",
    "CapacityConsistencyGateResult",
    "NightlyCapacityMaintenanceResult",
    "compute_expanded_capacity",
    "is_expansion_active",
    "should_restore_baseline",
    "run_nightly_capacity_maintenance",
]


@dataclass(frozen=True, slots=True)
class ElasticCapacityPolicy:
    """Growth and restoration rules for the elastic hot site.

    ``minimum_growth`` and ``growth_factor`` control how far an expansion
    grows. ``baseline_headroom_ratio`` is the occupancy threshold (relative to
    the baseline) below which the nightly restores the baseline. The ratio
    must be inside (0, 1]. ``max_automatic_deactivations`` caps how many
    low-retention memories one nightly soft-prune may deactivate.
    """

    minimum_growth: int = DEFAULT_CAPACITY_MINIMUM_GROWTH
    growth_factor: float = DEFAULT_CAPACITY_GROWTH_FACTOR
    baseline_headroom_ratio: float = DEFAULT_BASELINE_HEADROOM_RATIO
    max_automatic_deactivations: int = DEFAULT_MAX_AUTOMATIC_DEACTIVATIONS

    def validate(self) -> None:
        if self.minimum_growth < 1:
            raise ValueError(
                "minimum_growth must be at least 1."
            )
        if self.growth_factor <= 1.0:
            raise ValueError(
                "growth_factor must be strictly greater than 1.0."
            )
        if not 0.0 < self.baseline_headroom_ratio <= 1.0:
            raise ValueError(
                "baseline_headroom_ratio must be inside (0, 1]."
            )
        if self.max_automatic_deactivations < 1:
            raise ValueError(
                "max_automatic_deactivations must be at least 1."
            )


@dataclass(frozen=True, slots=True)
class CapacityConsistencyGateResult:
    """Outcome of the hot-site consistency check before compaction."""

    passed: bool
    active_metadata_records: int
    active_titan_items: int
    metadata_records: int
    discrepancies: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "active_metadata_records": self.active_metadata_records,
            "active_titan_items": self.active_titan_items,
            "metadata_records": self.metadata_records,
            "discrepancies": list(self.discrepancies),
        }


@dataclass(frozen=True, slots=True)
class NightlyCapacityMaintenanceResult:
    """Structured result of one elastic capacity maintenance run.

    The field order and to_dict() payload are a fixed 12-key contract used by
    the nightly runner and the operational status files.
    """

    capacity_before: int
    capacity_after: int
    active_before: int
    active_after: int
    automatic_soft_forgets: int
    compaction_attempted: bool
    compaction_applied: bool
    shrink_attempted: bool
    shrink_applied: bool
    shrink_skipped_reason: str
    consistency_ok: bool
    cold_site_modified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "capacity_before": self.capacity_before,
            "capacity_after": self.capacity_after,
            "active_before": self.active_before,
            "active_after": self.active_after,
            "automatic_soft_forgets": self.automatic_soft_forgets,
            "compaction_attempted": self.compaction_attempted,
            "compaction_applied": self.compaction_applied,
            "shrink_attempted": self.shrink_attempted,
            "shrink_applied": self.shrink_applied,
            "shrink_skipped_reason": self.shrink_skipped_reason,
            "consistency_ok": self.consistency_ok,
            "cold_site_modified": self.cold_site_modified,
        }


def compute_expanded_capacity(
    current_capacity: int,
    *,
    active_count: int,
    required_slots: int = 0,
    policy: ElasticCapacityPolicy | None = None,
) -> int:
    """Return the expanded capacity that always fits existing items.

    The new capacity is the largest of:

    - current + minimum_growth
    - ceil(current * growth_factor)
    - active_count + required_slots

    Expansion never evicts: the returned value is always at least
    ``active_count + required_slots``.
    """

    if current_capacity <= 0:
        raise ValueError("current_capacity must be positive.")
    if active_count < 0:
        raise ValueError("active_count must be non-negative.")
    if required_slots < 0:
        raise ValueError("required_slots must be non-negative.")

    resolved_policy = policy or ElasticCapacityPolicy()
    resolved_policy.validate()

    target = max(
        current_capacity + resolved_policy.minimum_growth,
        math.ceil(current_capacity * resolved_policy.growth_factor),
        active_count + required_slots,
    )

    return int(target)


def is_expansion_active(
    current_capacity: int,
    baseline_capacity: int,
) -> bool:
    """Return True when the hot site currently exceeds its baseline."""

    if current_capacity <= 0:
        raise ValueError("current_capacity must be positive.")
    if baseline_capacity <= 0:
        raise ValueError("baseline_capacity must be positive.")

    return current_capacity > baseline_capacity


def should_restore_baseline(
    active_count: int,
    *,
    baseline_capacity: int,
    headroom_ratio: float = DEFAULT_BASELINE_HEADROOM_RATIO,
) -> bool:
    """Return True when the active population fits inside the baseline.

    Restoration requires the active population to be at or below
    ``floor(baseline_capacity * headroom_ratio)`` so the restored baseline
    keeps a healthy headroom margin.
    """

    if active_count < 0:
        raise ValueError("active_count must be non-negative.")
    if baseline_capacity <= 0:
        raise ValueError("baseline_capacity must be positive.")
    if not 0.0 < headroom_ratio <= 1.0:
        raise ValueError(
            "headroom_ratio must be inside (0, 1]."
        )

    return active_count <= math.floor(
        baseline_capacity * headroom_ratio
    )


def _build_pruning_inputs(
    memories: Sequence["ValidatedMemory"],
    now: datetime,
) -> list[HotMemoryPruningInput]:
    """Translate validated memories into explicit pruning measurements."""

    inputs: list[HotMemoryPruningInput] = []

    for memory in memories:
        metadata = dict(memory.metadata)

        try:
            created = datetime.fromisoformat(
                memory.created_at.replace("Z", "+00:00")
            )
            age_days = max(
                0.0,
                (now - created).total_seconds() / 86400.0,
            )
        except (ValueError, TypeError):
            age_days = 0.0

        inputs.append(
            HotMemoryPruningInput(
                memory_id=memory.memory_id,
                block_id=HOT_SITE_SCOPE,
                importance=float(
                    metadata.get("importance", 0.5)
                ),
                access_count=int(
                    metadata.get("access_count", 0)
                ),
                age_days=age_days,
                retrieval_score=float(
                    metadata.get("retrieval_score", 0.0)
                ),
                active=memory.active,
                pinned=bool(
                    metadata.get("pinned", False)
                ),
                human_validated=True,
                metadata=metadata,
            )
        )

    return inputs


def _cold_archive_fingerprint(
    path: str | Path,
) -> tuple[bool, int, str]:
    """Fingerprint one cold-site file without mutating anything.

    The tuple (exists, size_bytes, sha256) matches the equality semantics of
    ``memory.sync.snapshot_file`` so a file that appears, disappears, or
    changes during the run is always detected.
    """

    target = Path(path)

    if not target.exists():
        return (False, 0, hashlib.sha256(b"").hexdigest())

    payload = target.read_bytes()

    return (
        True,
        len(payload),
        hashlib.sha256(payload).hexdigest(),
    )


def _append_log_line(path: str | Path, payload: dict[str, Any]) -> None:
    """Append one JSON line to an operational log file."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(payload, ensure_ascii=False, sort_keys=True)
            + "\n"
        )


def run_nightly_capacity_maintenance(
    hot_site: "HotSiteTitanMemory",
    *,
    policy: ElasticCapacityPolicy | None = None,
    capacity_operations: "CapacityOperations | None" = None,
    run_reference: str,
    cold_archive_path: str | Path | None = None,
    log_path: str | Path | None = None,
) -> NightlyCapacityMaintenanceResult:
    """Run the elastic capacity maintenance when the hot site is expanded.

    The maintenance sequence is prune -> consistency gate -> compact -> shrink.
    When the hot site is not expanded, the run returns a no-op report without
    acquiring the capacity mutation lock, touching the store, or recording an
    event. Compaction and shrinking are skipped when the consistency gate
    fails.

    The nightly observes pressure with an explicit usage-only weight override
    (``PressureWeights(usage_ratio=1.0, ...)``), so the default
    ``SoftPruningPolicy`` (minimum_pressure 0.70) is reachable at >= 70%
    usage. Automatic soft-forgets are always applied by the fixed
    ``NIGHTLY_CAPACITY_REVIEWER`` and the forget reason references the run.
    """

    reference = run_reference.strip()

    if not reference:
        raise ValueError("run_reference must not be empty.")

    if capacity_operations is None:
        raise ValueError("capacity_operations must be provided.")

    resolved_policy = policy or ElasticCapacityPolicy()
    resolved_policy.validate()

    started = datetime.now(timezone.utc)

    capacity = hot_site.capacity_status()
    current_capacity = int(capacity["current_capacity"])
    resolved_baseline = int(capacity["baseline_capacity"])

    if resolved_baseline <= 0:
        raise ValueError("baseline_capacity must be positive.")
    if current_capacity <= 0:
        raise ValueError("current_capacity must be positive.")

    active_before = len(
        hot_site.list_memories(active_only=True)
    )

    if not is_expansion_active(
        current_capacity,
        resolved_baseline,
    ):
        return NightlyCapacityMaintenanceResult(
            capacity_before=current_capacity,
            capacity_after=current_capacity,
            active_before=active_before,
            active_after=active_before,
            automatic_soft_forgets=0,
            compaction_attempted=False,
            compaction_applied=False,
            shrink_attempted=False,
            shrink_applied=False,
            shrink_skipped_reason="",
            consistency_ok=False,
            cold_site_modified=False,
        )

    hot_site_dir = hot_site.neural_state_path.parent
    resolved_cold_path = Path(
        cold_archive_path
        if cold_archive_path is not None
        else hot_site_dir / "cold_archive_events.jsonl"
    )
    resolved_log_path = Path(
        log_path
        if log_path is not None
        else hot_site_dir / "capacity_maintenance.jsonl"
    )

    resolved_cold_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    resolved_log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cold_before = _cold_archive_fingerprint(
        resolved_cold_path
    )

    with capacity_operations.mutation_lock(
        "nightly_capacity_maintenance"
    ):
        pressure = observe_memory_pressure(
            PressureObservationInput(
                scope_id=HOT_SITE_SCOPE,
                used_items=active_before,
                capacity=current_capacity,
            ),
            weights=PressureWeights(
                usage_ratio=1.0,
                momentum=0.0,
                entropy=0.0,
                surprise=0.0,
                persistence=0.0,
            ),
        )

        inputs = _build_pruning_inputs(
            hot_site.list_memories(active_only=False),
            started,
        )

        plan = plan_soft_pruning(
            scope_id=HOT_SITE_SCOPE,
            memories=inputs,
            pressure=pressure,
        )

        # Lazy import keeps the gateway dependency edge out of module init so
        # the adaptive and hot-site layers never form an import cycle.
        from memory.gateway.capacity_control import (
            apply_soft_pruning_plan,
        )

        prune_report = apply_soft_pruning_plan(
            plan,
            hot_site,
            applied_by=NIGHTLY_CAPACITY_REVIEWER,
            reason=(
                "Nightly elastic capacity maintenance "
                f"for run {reference}."
            ),
            max_deactivations=(
                resolved_policy.max_automatic_deactivations
            ),
        )

        automatic_soft_forgets = len(
            prune_report.applied_memory_ids
        )

        gate = hot_site.consistency_gate()
        consistency_ok = gate.passed

        compaction_attempted = gate.passed
        compaction_applied = False
        active_after = active_before

        if gate.passed:
            compacted = hot_site.compact_inactive()
            compaction_applied = compacted > 0
            active_after = len(
                hot_site.list_memories(active_only=True)
            )
        else:
            active_after = sum(
                1
                for memory in hot_site.list_memories(
                    active_only=False
                )
                if memory.active
            )

        headroom_ratio = (
            resolved_policy.baseline_headroom_ratio
        )
        headroom_fits = should_restore_baseline(
            active_after,
            baseline_capacity=resolved_baseline,
            headroom_ratio=headroom_ratio,
        )

        shrink_attempted = gate.passed and headroom_fits

        if shrink_attempted:
            hot_site.shrink_to_baseline(
                active_count=active_after,
                headroom_ratio=headroom_ratio,
            )

        capacity_after = int(
            hot_site.capacity_status()["current_capacity"]
        )
        shrink_applied = (
            shrink_attempted
            and capacity_after == resolved_baseline
        )

        if not gate.passed:
            shrink_skipped_reason = (
                "consistency gate failed: "
                + "; ".join(gate.discrepancies)
            )
        elif not headroom_fits:
            headroom_floor = math.floor(
                resolved_baseline * headroom_ratio
            )
            shrink_skipped_reason = (
                f"active {active_after} exceeds floor("
                f"baseline * headroom) = {headroom_floor}"
            )
        else:
            shrink_skipped_reason = ""

        cold_after = _cold_archive_fingerprint(
            resolved_cold_path
        )

        if cold_after != cold_before:
            raise RuntimeError(
                "The cold archive changed during nightly "
                "capacity maintenance."
            )

        result = NightlyCapacityMaintenanceResult(
            capacity_before=current_capacity,
            capacity_after=capacity_after,
            active_before=active_before,
            active_after=active_after,
            automatic_soft_forgets=automatic_soft_forgets,
            compaction_attempted=compaction_attempted,
            compaction_applied=compaction_applied,
            shrink_attempted=shrink_attempted,
            shrink_applied=shrink_applied,
            shrink_skipped_reason=shrink_skipped_reason,
            consistency_ok=consistency_ok,
            cold_site_modified=False,
        )

        if (
            automatic_soft_forgets > 0
            or compaction_applied
            or shrink_applied
            or capacity_after != current_capacity
        ):
            capacity_operations.record(
                "capacity_maintained",
                result.to_dict(),
            )
            _append_log_line(
                resolved_log_path,
                result.to_dict(),
            )

        return result
