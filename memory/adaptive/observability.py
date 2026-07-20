"""Read-only observability, health metrics, and diagnostics for memoriX.

Part 27.1-27.5 audits existing telemetry, collects bounded runtime samples,
computes deterministic indicators, and builds a dry-run report. It never
writes runtime state, loads Titan, or scans the cold-site payloads.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class MemoryObservabilityStatus(str, Enum):
    INFO = "info"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MemoryMetricSeverity(str, Enum):
    INFO = "info"
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MemoryObservabilityAudit:
    retrieval_metrics_present: bool = True
    routing_metrics_present: bool = True
    retention_metrics_present: bool = True
    consolidation_metrics_present: bool = True
    topic_block_metrics_present: bool = True
    policy_metrics_present: bool = True
    persistent_snapshots_present: bool = False
    drift_detection_present: bool = False
    alert_registry_present: bool = False
    observations: tuple[str, ...] = (
        "runtime_metadata_and_lifecycle_registries_are_available",
        "existing_benchmarks_are_point_in_time_reports",
        "part_27_1_27_5_is_read_only_and_bounded",
    )
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    hot_site_modified: bool = False
    cold_site_modified: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observations"] = list(self.observations)
        return payload


@dataclass(frozen=True, slots=True)
class MemoryMetricSample:
    metric_name: str
    metric_value: float
    unit: str
    source: str
    sample_count: int = 1
    dimensions: tuple[tuple[str, str], ...] = ()
    recorded_at: str | None = None

    def validate(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("metric_name must not be empty.")
        if self.sample_count < 0:
            raise ValueError("sample_count must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unit": self.unit,
            "source": self.source,
            "sample_count": self.sample_count,
            "dimensions": dict(self.dimensions),
            "recorded_at": self.recorded_at,
        }


@dataclass(frozen=True, slots=True)
class MemoryMetricWindow:
    start_time: str | None
    end_time: str | None
    assessment_limit: int
    maximum_files: int
    maximum_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryObservabilityCollection:
    samples: tuple[MemoryMetricSample, ...]
    source_records: tuple[tuple[str, int], ...]
    malformed_record_count: int
    files_inspected: int
    bytes_inspected: int
    truncated: bool
    window: MemoryMetricWindow
    sources_used: tuple[str, ...]
    dry_run: bool = True
    registry_modified: bool = False
    runtime_modified: bool = False
    hot_site_modified: bool = False
    cold_site_modified: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples": [sample.to_dict() for sample in self.samples],
            "source_records": dict(self.source_records),
            "malformed_record_count": self.malformed_record_count,
            "files_inspected": self.files_inspected,
            "bytes_inspected": self.bytes_inspected,
            "truncated": self.truncated,
            "window": self.window.to_dict(),
            "sources_used": list(self.sources_used),
            "dry_run": self.dry_run,
            "registry_modified": self.registry_modified,
            "runtime_modified": self.runtime_modified,
            "hot_site_modified": self.hot_site_modified,
            "cold_site_modified": self.cold_site_modified,
            "neural_model_loaded": self.neural_model_loaded,
        }


@dataclass(frozen=True, slots=True)
class MemoryHealthIndicator:
    category: str
    score: float
    status: MemoryObservabilityStatus
    metrics: tuple[tuple[str, float], ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "score": self.score,
            "status": self.status.value,
            "metrics": dict(self.metrics),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True, slots=True)
class MemoryAlert:
    alert_id: str
    metric_name: str
    severity: MemoryMetricSeverity
    value: float
    threshold: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload


@dataclass(frozen=True, slots=True)
class MemoryObservabilityReport:
    overall_health_score: float
    status: MemoryObservabilityStatus
    indicators: tuple[MemoryHealthIndicator, ...]
    alerts: tuple[MemoryAlert, ...]
    recommendations: tuple[str, ...]
    insufficient_data: tuple[str, ...]
    collection: MemoryObservabilityCollection
    dry_run: bool = True
    snapshot_saved: bool = False
    alert_saved: bool = False
    registry_modified: bool = False
    runtime_modified: bool = False
    hot_site_modified: bool = False
    cold_site_modified: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_health_score": self.overall_health_score,
            "status": self.status.value,
            "indicators": [indicator.to_dict() for indicator in self.indicators],
            "alerts": [alert.to_dict() for alert in self.alerts],
            "recommendations": list(self.recommendations),
            "insufficient_data": list(self.insufficient_data),
            "collection": self.collection.to_dict(),
            "dry_run": self.dry_run,
            "snapshot_saved": self.snapshot_saved,
            "alert_saved": self.alert_saved,
            "registry_modified": self.registry_modified,
            "runtime_modified": self.runtime_modified,
            "hot_site_modified": self.hot_site_modified,
            "cold_site_modified": self.cold_site_modified,
            "neural_model_loaded": self.neural_model_loaded,
        }


def audit_memory_observability() -> MemoryObservabilityAudit:
    return MemoryObservabilityAudit()


def _read_jsonl_bounded(path: Path, *, limit: int, maximum_bytes: int) -> tuple[list[dict[str, Any]], int, int, bool]:
    if not path.exists() or not path.is_file():
        return [], 0, 0, False
    records: list[dict[str, Any]] = []
    malformed = 0
    bytes_read = 0
    truncated = False
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            encoded_size = len(line.encode("utf-8"))
            if bytes_read + encoded_size > maximum_bytes or len(records) >= limit:
                truncated = True
                break
            bytes_read += encoded_size
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(payload, Mapping):
                records.append(dict(payload))
            else:
                malformed += 1
    return records, malformed, bytes_read, truncated


def _read_json_object(path: Path, *, maximum_bytes: int) -> tuple[dict[str, Any], int, int, bool]:
    if not path.exists() or not path.is_file():
        return {}, 0, 0, False
    size = path.stat().st_size
    if size > maximum_bytes:
        return {}, 0, 0, True
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}, 1, size, False
    if not isinstance(payload, Mapping):
        return {}, 1, size, False
    return dict(payload), 0, size, False


def _latest_by_id(records: Sequence[Mapping[str, Any]], id_key: str) -> tuple[dict[str, Any], ...]:
    latest: dict[str, dict[str, Any]] = {}
    anonymous: list[dict[str, Any]] = []
    for record in records:
        identifier = record.get(id_key)
        if identifier is None:
            anonymous.append(dict(record))
            continue
        latest[str(identifier)] = dict(record)
    return tuple((*latest.values(), *anonymous))


def _ratio(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    if denominator <= 0:
        return default
    return round(max(0.0, min(1.0, numerator / denominator)), 6)


def collect_memory_observability_samples(
    runtime_root: str | Path,
    *,
    assessment_limit: int = 1000,
    maximum_files: int = 8,
    maximum_bytes: int = 2_000_000,
    start_time: str | None = None,
    end_time: str | None = None,
    metric_names: Iterable[str] | None = None,
    topic_block_id: str | None = None,
    policy_version_id: str | None = None,
) -> MemoryObservabilityCollection:
    if assessment_limit <= 0:
        raise ValueError("assessment_limit must be positive.")
    if maximum_files <= 0 or maximum_bytes <= 0:
        raise ValueError("maximum_files and maximum_bytes must be positive.")

    root = Path(runtime_root)
    source_specs = (
        ("hot_metadata", root / "hot_site" / "titan_metadata.jsonl", "jsonl", "memory_id"),
        ("topic_blocks", root / "topic_blocks" / "topic_blocks.jsonl", "jsonl", "block_id"),
        ("topic_assignments", root / "topic_blocks" / "topic_assignments.jsonl", "jsonl", "item_id"),
        ("consolidation_plans", root / "consolidation" / "plans.jsonl", "jsonl", "plan_id"),
        ("consolidation_sessions", root / "consolidation" / "sessions.jsonl", "jsonl", "session_id"),
        ("policy_versions", root / "policies" / "policy_versions.jsonl", "jsonl", "version_id"),
        ("topic_state", root / "topic_blocks" / "topic_block_state.json", "json", None),
        ("policy_state", root / "policies" / "policy_state.json", "json", None),
    )
    requested = None if metric_names is None else {str(value) for value in metric_names}
    loaded: dict[str, Any] = {}
    source_records: list[tuple[str, int]] = []
    sources_used: list[str] = []
    malformed = 0
    files_inspected = 0
    bytes_inspected = 0
    truncated = False
    remaining_bytes = maximum_bytes

    for source_name, path, source_type, id_key in source_specs[:maximum_files]:
        if remaining_bytes <= 0:
            truncated = True
            break
        if source_type == "jsonl":
            records, bad, used, was_truncated = _read_jsonl_bounded(
                path,
                limit=assessment_limit,
                maximum_bytes=remaining_bytes,
            )
            value: Any = _latest_by_id(records, str(id_key))
            count = len(value)
        else:
            value, bad, used, was_truncated = _read_json_object(path, maximum_bytes=remaining_bytes)
            count = 1 if value else 0
        if path.exists() and path.is_file():
            files_inspected += 1
            sources_used.append(source_name)
        loaded[source_name] = value
        source_records.append((source_name, count))
        malformed += bad
        bytes_inspected += used
        remaining_bytes -= used
        truncated = truncated or was_truncated

    memories = tuple(loaded.get("hot_metadata", ()))
    if topic_block_id is not None:
        memories = tuple(
            record for record in memories
            if str((record.get("metadata") or {}).get("topic_block_id", record.get("topic_block_id", ""))) == topic_block_id
        )
    active_count = sum(1 for record in memories if bool(record.get("active", True)))
    inactive_count = max(0, len(memories) - active_count)
    protected_count = sum(
        1 for record in memories
        if bool(record.get("protected", (record.get("metadata") or {}).get("protected", False)))
    )
    superseded_count = sum(
        1 for record in memories
        if bool(record.get("superseded", False)) or bool(record.get("superseded_by_memory_id"))
    )
    hot_capacity = max(
        [int(record.get("capacity", 0) or 0) for record in memories if str(record.get("capacity", "")).isdigit()] or [0]
    )
    hot_utilization = _ratio(len(memories), hot_capacity) if hot_capacity else min(1.0, len(memories) / max(assessment_limit, 1))

    blocks = tuple(loaded.get("topic_blocks", ()))
    active_blocks = [record for record in blocks if str(record.get("status", "active")) in {"active", "protected", "overloaded"}]
    overloaded_blocks = [record for record in blocks if str(record.get("status", "")) == "overloaded"]
    archived_blocks = [record for record in blocks if str(record.get("status", "")) in {"archived", "merged"}]
    block_counts = [max(0, int(record.get("memory_count", 0) or 0)) for record in active_blocks]
    total_block_memories = sum(block_counts)
    largest_block_ratio = _ratio(max(block_counts) if block_counts else 0, total_block_memories)
    general_count = sum(
        max(0, int(record.get("memory_count", 0) or 0))
        for record in active_blocks
        if str(record.get("canonical_topic", record.get("label", ""))).lower() == "general"
    )

    assignments = tuple(loaded.get("topic_assignments", ()))
    fallback_assignments = sum(
        1 for record in assignments
        if str(record.get("block_id", record.get("target_block_id", ""))) == "block_general"
    )

    plans = tuple(loaded.get("consolidation_plans", ()))
    sessions = tuple(loaded.get("consolidation_sessions", ()))
    plan_statuses = [str(record.get("status", "")) for record in plans]
    session_statuses = [str(record.get("status", "")) for record in sessions]

    policy_versions = tuple(loaded.get("policy_versions", ()))
    if policy_version_id is not None:
        policy_versions = tuple(record for record in policy_versions if str(record.get("version_id", "")) == policy_version_id)
    active_policy = str((loaded.get("policy_state") or {}).get("active_policy_version_id", ""))

    raw_metrics = {
        "hot_site_utilization": hot_utilization,
        "protected_memory_ratio": _ratio(protected_count, len(memories)),
        "inactive_memory_ratio": _ratio(inactive_count, len(memories)),
        "superseded_memory_ratio": _ratio(superseded_count, len(memories)),
        "active_block_count": float(len(active_blocks)),
        "overloaded_block_count": float(len(overloaded_blocks)),
        "archived_block_count": float(len(archived_blocks)),
        "largest_block_ratio": largest_block_ratio,
        "general_block_ratio": _ratio(general_count, total_block_memories),
        "routing_fallback_rate": _ratio(fallback_assignments, len(assignments)),
        "plans_created": float(len(plans)),
        "plans_approved": float(plan_statuses.count("approved")),
        "plans_rejected": float(plan_statuses.count("rejected")),
        "sessions_completed": float(session_statuses.count("completed")),
        "sessions_failed": float(session_statuses.count("failed")),
        "recovery_rate": _ratio(session_statuses.count("recovered"), len(sessions)),
        "policy_change_count": float(len(policy_versions)),
        "active_policy_present": 1.0 if active_policy else 0.0,
        "malformed_record_rate": _ratio(malformed, sum(count for _, count in source_records) + malformed),
    }
    samples = tuple(
        MemoryMetricSample(
            metric_name=name,
            metric_value=value,
            unit="ratio" if name.endswith("_ratio") or name.endswith("_rate") or name.endswith("_utilization") or name == "active_policy_present" else "count",
            source="runtime_observability",
            sample_count=sum(count for _, count in source_records),
            dimensions=tuple(
                (key, value)
                for key, value in (
                    ("topic_block_id", topic_block_id),
                    ("policy_version_id", policy_version_id),
                )
                if value is not None
            ),
        )
        for name, value in sorted(raw_metrics.items())
        if requested is None or name in requested
    )
    return MemoryObservabilityCollection(
        samples=samples,
        source_records=tuple(source_records),
        malformed_record_count=malformed,
        files_inspected=files_inspected,
        bytes_inspected=bytes_inspected,
        truncated=truncated,
        window=MemoryMetricWindow(start_time, end_time, assessment_limit, maximum_files, maximum_bytes),
        sources_used=tuple(sources_used),
    )


def _status_for_score(score: float) -> MemoryObservabilityStatus:
    if score >= 0.8:
        return MemoryObservabilityStatus.HEALTHY
    if score >= 0.55:
        return MemoryObservabilityStatus.WARNING
    return MemoryObservabilityStatus.CRITICAL


def calculate_memory_health_indicators(collection: MemoryObservabilityCollection) -> tuple[MemoryHealthIndicator, ...]:
    values = {sample.metric_name: sample.metric_value for sample in collection.samples}
    indicators: list[MemoryHealthIndicator] = []

    capacity_score = round(1.0 - max(values.get("hot_site_utilization", 0.0) - 0.5, 0.0) * 1.6, 6)
    indicators.append(MemoryHealthIndicator(
        "capacity_pressure",
        max(0.0, min(1.0, capacity_score)),
        _status_for_score(capacity_score),
        tuple((name, values.get(name, 0.0)) for name in ("hot_site_utilization", "inactive_memory_ratio", "protected_memory_ratio")),
        ("hot_site_pressure_is_derived_from_bounded_metadata",),
    ))

    topic_score = round(1.0 - max(values.get("largest_block_ratio", 0.0) - 0.4, 0.0) - values.get("general_block_ratio", 0.0) * 0.35 - min(0.4, values.get("overloaded_block_count", 0.0) * 0.1), 6)
    indicators.append(MemoryHealthIndicator(
        "topic_block_health",
        max(0.0, min(1.0, topic_score)),
        _status_for_score(topic_score),
        tuple((name, values.get(name, 0.0)) for name in ("largest_block_ratio", "general_block_ratio", "overloaded_block_count")),
        ("large_or_general_blocks_reduce_topic_health",),
    ))

    consolidation_total = values.get("sessions_completed", 0.0) + values.get("sessions_failed", 0.0)
    consolidation_score = 1.0 if consolidation_total == 0 else _ratio(values.get("sessions_completed", 0.0), consolidation_total)
    indicators.append(MemoryHealthIndicator(
        "consolidation_quality",
        consolidation_score,
        _status_for_score(consolidation_score),
        tuple((name, values.get(name, 0.0)) for name in ("sessions_completed", "sessions_failed", "recovery_rate")),
        ("no_completed_sessions_is_reported_as_insufficient_data",) if consolidation_total == 0 else (),
    ))

    integrity_score = round(1.0 - values.get("malformed_record_rate", 0.0), 6)
    indicators.append(MemoryHealthIndicator(
        "runtime_integrity",
        integrity_score,
        _status_for_score(integrity_score),
        (("malformed_record_rate", values.get("malformed_record_rate", 0.0)),),
        ("malformed_runtime_records_reduce_integrity",),
    ))
    return tuple(indicators)


def build_memory_observability_report(collection: MemoryObservabilityCollection) -> MemoryObservabilityReport:
    indicators = calculate_memory_health_indicators(collection)
    values = {sample.metric_name: sample.metric_value for sample in collection.samples}
    alerts: list[MemoryAlert] = []
    thresholds = (
        ("hot_site_utilization", 0.8, "hot_site_pressure_is_high"),
        ("largest_block_ratio", 0.7, "one_topic_block_dominates_the_registry"),
        ("general_block_ratio", 0.5, "general_topic_usage_is_high"),
        ("routing_fallback_rate", 0.4, "routing_fallback_usage_is_high"),
        ("malformed_record_rate", 0.05, "runtime_contains_malformed_records"),
    )
    for metric_name, threshold, explanation in thresholds:
        value = values.get(metric_name)
        if value is None or value < threshold:
            continue
        severity = MemoryMetricSeverity.CRITICAL if value >= min(1.0, threshold + 0.15) else MemoryMetricSeverity.WARNING
        alerts.append(MemoryAlert(
            alert_id=f"alert_{metric_name}",
            metric_name=metric_name,
            severity=severity,
            value=value,
            threshold=threshold,
            explanation=explanation,
        ))

    insufficient: list[str] = []
    source_counts = dict(collection.source_records)
    if source_counts.get("hot_metadata", 0) == 0:
        insufficient.append("hot_site_metadata_unavailable")
    if source_counts.get("topic_blocks", 0) == 0:
        insufficient.append("topic_block_registry_unavailable")
    if source_counts.get("consolidation_sessions", 0) == 0:
        insufficient.append("consolidation_history_unavailable")
    if source_counts.get("policy_versions", 0) == 0:
        insufficient.append("policy_history_unavailable")

    overall = round(sum(indicator.score for indicator in indicators) / len(indicators), 6) if indicators else 0.0
    status = MemoryObservabilityStatus.UNKNOWN if not collection.sources_used else _status_for_score(overall)
    recommendations = tuple(
        dict.fromkeys(
            [
                "review_hot_site_capacity" if any(alert.metric_name == "hot_site_utilization" for alert in alerts) else "keep_capacity_monitoring",
                "review_topic_block_balance" if any(alert.metric_name in {"largest_block_ratio", "general_block_ratio"} for alert in alerts) else "keep_topic_block_monitoring",
                "repair_malformed_runtime_records" if collection.malformed_record_count else "keep_runtime_integrity_checks",
            ]
        )
    )
    return MemoryObservabilityReport(
        overall_health_score=overall,
        status=status,
        indicators=indicators,
        alerts=tuple(alerts),
        recommendations=recommendations,
        insufficient_data=tuple(insufficient),
        collection=collection,
    )
