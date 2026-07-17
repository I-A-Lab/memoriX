"""Read-only runtime capacity inspection for memoriX.

The inspector reads persisted metadata only. It never loads Titan neural
weights, writes runtime files, expands capacity, prunes memory, validates a
candidate, or touches the cold site.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from memory.adaptive.contracts import PressureLevel
from memory.data import CandidateStatus, MemoryStoragePaths
from memory.data.jsonl_store import read_json_lines
from memory.data.paths import MEMORY_PACKAGE_ROOT


WATCH_RATIO = 0.80
HIGH_RATIO = 0.90


@dataclass(frozen=True, slots=True)
class RuntimeCapacitySnapshot:
    """Immutable observation of hot-site capacity and related runtime files."""

    status: str
    runtime_root: str
    configured_capacity: int
    active_memories: int
    inactive_memories: int
    metadata_records: int
    pending_candidates: int
    available_slots: int
    usage_ratio: float
    pressure_level: PressureLevel
    admission_allowed: bool
    simulated: bool
    file_sizes_bytes: dict[str, int]
    observation_only: bool = True
    applies_changes: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["pressure_level"] = self.pressure_level.value
        return payload


def validate_external_runtime_root(runtime_root: str | Path) -> Path:
    """Resolve a runtime root and reject paths inside the source repository."""

    root = Path(runtime_root).expanduser().resolve()
    repository_root = MEMORY_PACKAGE_ROOT.parent.resolve()

    try:
        root.relative_to(repository_root)
    except ValueError:
        return root

    raise ValueError(
        "The memoriX runtime root must remain outside the repository."
    )


def classify_runtime_pressure(
    active_memories: int,
    configured_capacity: int,
) -> PressureLevel:
    """Classify bounded hot-site usage with deterministic thresholds."""

    if active_memories < 0:
        raise ValueError("active_memories must be non-negative.")

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")

    usage_ratio = active_memories / configured_capacity

    if usage_ratio >= 1.0:
        return PressureLevel.CRITICAL

    if usage_ratio >= HIGH_RATIO:
        return PressureLevel.HIGH

    if usage_ratio >= WATCH_RATIO:
        return PressureLevel.WATCH

    return PressureLevel.STABLE


def _latest_metadata_counts(
    metadata_records: list[dict[str, Any]],
) -> tuple[int, int]:
    latest_by_memory_id: dict[str, dict[str, Any]] = {}

    for record in metadata_records:
        memory_id = str(
            record.get("memory_id")
            or record.get("id")
            or ""
        ).strip()

        if memory_id:
            latest_by_memory_id[memory_id] = record

    active = sum(
        1
        for record in latest_by_memory_id.values()
        if bool(record.get("active", True))
    )
    inactive = len(latest_by_memory_id) - active
    return active, inactive


def _pending_candidate_count(
    candidate_records: list[dict[str, Any]],
) -> int:
    return sum(
        1
        for record in candidate_records
        if str(record.get("status", "pending"))
        == CandidateStatus.PENDING.value
    )


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def inspect_runtime_capacity(
    *,
    runtime_root: str | Path,
    configured_capacity: int,
    simulated_active_items: int | None = None,
    simulated_inactive_items: int = 0,
    simulated_pending_candidates: int = 0,
) -> RuntimeCapacitySnapshot:
    """Inspect real metadata or calculate a synthetic capacity snapshot.

    Supplying ``simulated_active_items`` switches the function to a fully
    synthetic calculation. In that mode no runtime file is read or created.
    """

    root = validate_external_runtime_root(runtime_root)

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")

    for name, value in (
        ("simulated_inactive_items", simulated_inactive_items),
        ("simulated_pending_candidates", simulated_pending_candidates),
    ):
        if value < 0:
            raise ValueError(f"{name} must be non-negative.")

    paths = MemoryStoragePaths.from_runtime_root(root)
    simulated = simulated_active_items is not None

    if simulated:
        if simulated_active_items is None or simulated_active_items < 0:
            raise ValueError(
                "simulated_active_items must be non-negative."
            )

        active_memories = simulated_active_items
        inactive_memories = simulated_inactive_items
        metadata_record_count = (
            active_memories + inactive_memories
        )
        pending_candidates = simulated_pending_candidates
        file_sizes = {
            "titan_metadata": 0,
            "titan_neural_state": 0,
            "memory_candidates": 0,
            "short_term_events": 0,
            "cold_archive_events": 0,
        }
    else:
        metadata_records = read_json_lines(paths.titan_metadata)
        candidate_records = read_json_lines(paths.memory_candidates)
        active_memories, inactive_memories = (
            _latest_metadata_counts(metadata_records)
        )
        metadata_record_count = len(metadata_records)
        pending_candidates = _pending_candidate_count(
            candidate_records
        )
        file_sizes = {
            "titan_metadata": _file_size(paths.titan_metadata),
            "titan_neural_state": _file_size(
                paths.titan_neural_state
            ),
            "memory_candidates": _file_size(
                paths.memory_candidates
            ),
            "short_term_events": _file_size(
                paths.short_term_events
            ),
            "cold_archive_events": _file_size(
                paths.cold_archive_events
            ),
        }

    usage_ratio = active_memories / configured_capacity
    available_slots = max(
        0,
        configured_capacity - active_memories,
    )
    pressure_level = classify_runtime_pressure(
        active_memories,
        configured_capacity,
    )

    return RuntimeCapacitySnapshot(
        status="ok",
        runtime_root=str(root),
        configured_capacity=configured_capacity,
        active_memories=active_memories,
        inactive_memories=inactive_memories,
        metadata_records=metadata_record_count,
        pending_candidates=pending_candidates,
        available_slots=available_slots,
        usage_ratio=usage_ratio,
        pressure_level=pressure_level,
        admission_allowed=(active_memories < configured_capacity),
        simulated=simulated,
        file_sizes_bytes=file_sizes,
    )
