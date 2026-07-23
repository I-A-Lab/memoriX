"""Read-only pressure inspection from persisted Titan metadata."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from memory.adaptive.memory_pressure import (
    HotSitePressureSnapshot,
    MemoryPressureAssessment,
    MemoryPressureInput,
    assess_memory_pressure,
    observe_hot_site_pressure,
)
from memory.adaptive.runtime_capacity import validate_external_runtime_root
from memory.data import MemoryStoragePaths
from memory.data.jsonl_store import read_json_lines


def _finite_number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest_records(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
        if memory_id:
            latest[memory_id] = record
    return latest


def pressure_input_from_metadata(
    record: Mapping[str, Any],
    *,
    observed_at: datetime,
    replaced_memory_ids: set[str] | None = None,
) -> MemoryPressureInput:
    memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
    if not memory_id:
        raise ValueError("Titan metadata record has no memory_id.")
    metadata = dict(record.get("metadata") or {})
    created = _parse_timestamp(
        metadata.get("created_at")
        or metadata.get("validated_at")
        or record.get("stored_at")
    )
    age_days = 0.0 if created is None else max(0.0, (observed_at - created).total_seconds() / 86400.0)
    replaced = memory_id in (replaced_memory_ids or set()) or bool(metadata.get("replaced", False))
    protected = bool(metadata.get("pinned", metadata.get("protected", False)))
    return MemoryPressureInput(
        memory_id=memory_id,
        age_days=age_days,
        access_count=int(max(0.0, _finite_number(metadata.get("access_count", record.get("access_count", 0))))),
        importance=_finite_number(metadata.get("importance", record.get("importance", 0.5)), 0.5),
        momentum=_finite_number(metadata.get("momentum", record.get("momentum", 0.0))),
        surprise=_finite_number(metadata.get("surprise", record.get("surprise", 0.0))),
        active=bool(record.get("active", metadata.get("active", True))),
        replaced=replaced,
        protected=protected,
        metadata=metadata,
        observed_at=observed_at.isoformat(),
    )


@dataclass(frozen=True, slots=True)
class RuntimeMemoryPressureReport:
    status: str
    runtime_root: str
    simulated: bool
    metadata_records: int
    unique_memories: int
    assessment_limit: int
    assessments_truncated: bool
    snapshot: HotSitePressureSnapshot
    observation_only: bool = True
    applies_changes: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["snapshot"] = self.snapshot.to_dict()
        return payload


def inspect_runtime_memory_pressure(
    *,
    runtime_root: str | Path,
    assessment_limit: int = 100,
    simulated_memory_count: int | None = None,
    observed_at: str | None = None,
) -> RuntimeMemoryPressureReport:
    root = validate_external_runtime_root(runtime_root)
    if assessment_limit < 0:
        raise ValueError("assessment_limit must be non-negative.")
    now = _parse_timestamp(observed_at) if observed_at else datetime.now(timezone.utc)
    if now is None:
        raise ValueError("observed_at must be an ISO-8601 timestamp.")

    if simulated_memory_count is not None:
        if simulated_memory_count < 0:
            raise ValueError("simulated_memory_count must be non-negative.")
        sample = MemoryPressureInput(
            memory_id="simulated_obsolete_memory",
            age_days=730,
            access_count=0,
            importance=0.0,
            momentum=0.0,
            surprise=0.0,
            active=False,
            replaced=True,
            observed_at=now.isoformat(),
        )
        item = assess_memory_pressure(sample, assessment_id="simulated_assessment")
        level_counts = {level: 0 for level in ("stable", "watch", "high", "critical")}
        if simulated_memory_count:
            level_counts[item.level.value] = simulated_memory_count
        snapshot = HotSitePressureSnapshot(
            snapshot_id="simulated_hot_site_pressure",
            observed_at=now.isoformat(),
            memory_count=simulated_memory_count,
            mean_pressure=item.pressure_score if simulated_memory_count else 0.0,
            maximum_pressure=item.pressure_score if simulated_memory_count else 0.0,
            level_counts=level_counts,
            protected_count=0,
            inactive_count=simulated_memory_count,
            replaced_count=simulated_memory_count,
            pruning_candidate_count=simulated_memory_count,
            assessments=(item,) if simulated_memory_count and assessment_limit else (),
        )
        return RuntimeMemoryPressureReport(
            status="ok",
            runtime_root=str(root),
            simulated=True,
            metadata_records=0,
            unique_memories=simulated_memory_count,
            assessment_limit=assessment_limit,
            assessments_truncated=simulated_memory_count > len(snapshot.assessments),
            snapshot=snapshot,
        )

    paths = MemoryStoragePaths.from_runtime_root(root)
    records = read_json_lines(paths.titan_metadata)
    latest = _latest_records(records)
    replaced_ids = {
        str((record.get("metadata") or {}).get("supersedes_memory_id")).strip()
        for record in latest.values()
        if (record.get("metadata") or {}).get("supersedes_memory_id")
    }
    inputs = tuple(
        pressure_input_from_metadata(record, observed_at=now, replaced_memory_ids=replaced_ids)
        for _, record in sorted(latest.items())
    )
    full = observe_hot_site_pressure(inputs, observed_at=now.isoformat(), snapshot_id="runtime_hot_site_pressure")
    limited_assessments = full.assessments[:assessment_limit]
    limited = HotSitePressureSnapshot(
        snapshot_id=full.snapshot_id,
        observed_at=full.observed_at,
        memory_count=full.memory_count,
        mean_pressure=full.mean_pressure,
        maximum_pressure=full.maximum_pressure,
        level_counts=full.level_counts,
        protected_count=full.protected_count,
        inactive_count=full.inactive_count,
        replaced_count=full.replaced_count,
        pruning_candidate_count=full.pruning_candidate_count,
        assessments=limited_assessments,
    )
    return RuntimeMemoryPressureReport(
        status="ok",
        runtime_root=str(root),
        simulated=False,
        metadata_records=len(records),
        unique_memories=len(latest),
        assessment_limit=assessment_limit,
        assessments_truncated=len(full.assessments) > len(limited_assessments),
        snapshot=limited,
    )


def inspect_runtime_memory_pressure_item(
    *, runtime_root: str | Path, memory_id: str, observed_at: str | None = None,
) -> MemoryPressureAssessment | None:
    target = memory_id.strip()
    if not target:
        raise ValueError("memory_id must be non-empty.")
    report = inspect_runtime_memory_pressure(runtime_root=runtime_root, assessment_limit=1_000_000, observed_at=observed_at)
    for assessment in report.snapshot.assessments:
        if assessment.memory_id == target:
            return assessment
    return None
