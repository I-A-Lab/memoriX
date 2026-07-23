"""Read-only live probe for a memoriX runtime directory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from memory.data.paths import MemoryStoragePaths
from memory.diagnostics.contracts import (
    LiveProbeReport,
    ProbeCheck,
    ProbeCheckStatus,
    ProbeStatus,
    RuntimeFileObservation,
)
from memory.diagnostics.file_inspection import (
    inspect_runtime_path,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_runtime_paths(
    runtime_root: Path,
) -> dict[str, Path]:
    """Return canonical and optional runtime paths.

    Canonical storage paths come from MemoryStoragePaths, which is the
    single source of truth used by the memoriX gateway. Optional adaptive
    paths remain observation-only and are resolved relative to the same
    runtime root.

    Missing paths are legitimate observations. This function performs no
    mkdir, touch, write, migration, or storage initialization.
    """

    storage_paths = (
        MemoryStoragePaths.from_runtime_root(
            runtime_root
        )
    )
    root = storage_paths.runtime_root

    return {
        "runtime_root": root,
        "short_term_root": (
            storage_paths.short_term_events.parent
        ),
        "short_term_events": (
            storage_paths.short_term_events
        ),
        "cold_root": (
            storage_paths.cold_archive_events.parent
        ),
        "cold_archive_events": (
            storage_paths.cold_archive_events
        ),
        "candidates_root": (
            storage_paths.memory_candidates.parent
        ),
        "memory_candidates": (
            storage_paths.memory_candidates
        ),
        "hot_root": (
            storage_paths.titan_neural_state.parent
        ),
        "titan_neural_state": (
            storage_paths.titan_neural_state
        ),
        "titan_metadata": (
            storage_paths.titan_metadata
        ),
        "logs_root": (
            storage_paths.nightly_logs.parent
        ),
        "nightly_logs": (
            storage_paths.nightly_logs
        ),
        "adaptive_root": (
            root / "adaptive"
        ),
        "topic_blocks": (
            root
            / "adaptive"
            / "topic_blocks.json"
        ),
        "pressure_history": (
            root
            / "adaptive"
            / "pressure_history.jsonl"
        ),
        "capacity_history": (
            root
            / "adaptive"
            / "capacity_recommendations.jsonl"
        ),
        "pruning_history": (
            root
            / "adaptive"
            / "pruning_plans.jsonl"
        ),
        "controller_history": (
            root
            / "adaptive"
            / "controller_decisions.jsonl"
        ),
    }

def _file_integrity_check(
    observations: tuple[
        RuntimeFileObservation,
        ...
    ],
) -> ProbeCheck:
    invalid = [
        item
        for item in observations
        if (
            item.error is not None
            or item.valid_json is False
            or item.valid_jsonl is False
        )
    ]

    if invalid:
        return ProbeCheck(
            check_id="runtime_file_integrity",
            status=ProbeCheckStatus.FAIL,
            message=(
                "One or more runtime files could not "
                "be parsed safely."
            ),
            details={
                "invalid_paths": [
                    item.path
                    for item in invalid
                ],
            },
        )

    return ProbeCheck(
        check_id="runtime_file_integrity",
        status=ProbeCheckStatus.PASS,
        message=(
            "All discovered JSON and JSONL files "
            "are structurally readable."
        ),
        details={
            "inspected_path_count": len(
                observations
            ),
        },
    )


def _runtime_presence_check(
    runtime_root: Path,
) -> ProbeCheck:
    if not runtime_root.exists():
        return ProbeCheck(
            check_id="runtime_presence",
            status=ProbeCheckStatus.FAIL,
            message="Runtime root does not exist.",
            details={
                "runtime_root": str(runtime_root),
            },
        )

    if not runtime_root.is_dir():
        return ProbeCheck(
            check_id="runtime_presence",
            status=ProbeCheckStatus.FAIL,
            message=(
                "Runtime root exists but is not a directory."
            ),
            details={
                "runtime_root": str(runtime_root),
            },
        )

    return ProbeCheck(
        check_id="runtime_presence",
        status=ProbeCheckStatus.PASS,
        message="Runtime root is available.",
        details={
            "runtime_root": str(runtime_root),
        },
    )


def _cold_contract_check(
    observations: tuple[
        RuntimeFileObservation,
        ...
    ],
) -> ProbeCheck:
    cold_items = [
        item
        for item in observations
        if item.logical_name.startswith(
            "cold_"
        )
    ]

    invalid = [
        item
        for item in cold_items
        if (
            item.error is not None
            or item.valid_json is False
            or item.valid_jsonl is False
        )
    ]

    if invalid:
        return ProbeCheck(
            check_id="cold_archive_readability",
            status=ProbeCheckStatus.FAIL,
            message=(
                "A cold-site file is unreadable."
            ),
            details={
                "invalid_paths": [
                    item.path
                    for item in invalid
                ],
            },
        )

    existing = [
        item
        for item in cold_items
        if item.exists
    ]

    if not existing:
        return ProbeCheck(
            check_id="cold_archive_readability",
            status=ProbeCheckStatus.NOT_APPLICABLE,
            message=(
                "No known cold-site path was found."
            ),
            details={},
        )

    return ProbeCheck(
        check_id="cold_archive_readability",
        status=ProbeCheckStatus.PASS,
        message=(
            "Existing cold-site paths are readable."
        ),
        details={
            "existing_cold_paths": len(existing),
        },
    )


def _adaptive_contract_check(
    observations: tuple[
        RuntimeFileObservation,
        ...
    ],
) -> ProbeCheck:
    adaptive_items = [
        item
        for item in observations
        if (
            item.logical_name.startswith(
                "adaptive_"
            )
            or item.logical_name
            in {
                "topic_blocks",
                "pressure_history",
                "capacity_history",
                "pruning_history",
                "controller_history",
            }
        )
    ]

    existing = [
        item
        for item in adaptive_items
        if item.exists
    ]

    if not existing:
        return ProbeCheck(
            check_id="adaptive_runtime_state",
            status=ProbeCheckStatus.NOT_APPLICABLE,
            message=(
                "No persisted adaptive runtime state "
                "was discovered."
            ),
            details={
                "expected_mode": (
                    "observation_or_dry_run_only"
                ),
            },
        )

    invalid = [
        item
        for item in existing
        if (
            item.error is not None
            or item.valid_json is False
            or item.valid_jsonl is False
        )
    ]

    if invalid:
        return ProbeCheck(
            check_id="adaptive_runtime_state",
            status=ProbeCheckStatus.FAIL,
            message=(
                "Persisted adaptive state contains "
                "unreadable files."
            ),
            details={
                "invalid_paths": [
                    item.path
                    for item in invalid
                ],
            },
        )

    return ProbeCheck(
        check_id="adaptive_runtime_state",
        status=ProbeCheckStatus.PASS,
        message=(
            "Persisted adaptive state is readable."
        ),
        details={
            "existing_adaptive_paths": len(
                existing
            ),
        },
    )


def _aggregate_status(
    checks: tuple[ProbeCheck, ...],
) -> ProbeStatus:
    statuses = {
        check.status
        for check in checks
    }

    if ProbeCheckStatus.FAIL in statuses:
        return ProbeStatus.UNAVAILABLE

    if ProbeCheckStatus.WARN in statuses:
        return ProbeStatus.DEGRADED

    return ProbeStatus.HEALTHY


def run_live_probe(
    runtime_root: Path | str,
    *,
    probe_id: str | None = None,
    generated_at: str | None = None,
) -> LiveProbeReport:
    """Inspect a memoriX runtime without instantiating its services."""

    root = Path(runtime_root).resolve()
    paths = discover_runtime_paths(root)

    observations = tuple(
        inspect_runtime_path(
            logical_name,
            path,
        )
        for logical_name, path
        in paths.items()
    )

    checks = (
        _runtime_presence_check(root),
        _file_integrity_check(observations),
        _cold_contract_check(observations),
        _adaptive_contract_check(
            observations
        ),
        ProbeCheck(
            check_id="read_only_contract",
            status=ProbeCheckStatus.PASS,
            message=(
                "Probe used filesystem metadata and read-only "
                "file parsing only."
            ),
            details={
                "gateway_instantiated": False,
                "titan_loaded": False,
                "retrieval_called": False,
                "consolidation_called": False,
                "candidate_created": False,
                "memory_validated": False,
            },
        ),
    )

    counters = {
        "observed_paths": len(observations),
        "existing_paths": sum(
            item.exists
            for item in observations
        ),
        "existing_files": sum(
            item.exists and item.is_file
            for item in observations
        ),
        "existing_directories": sum(
            item.exists and item.is_directory
            for item in observations
        ),
        "reported_records": sum(
            item.record_count or 0
            for item in observations
        ),
        "checks_passed": sum(
            check.status
            is ProbeCheckStatus.PASS
            for check in checks
        ),
        "checks_warned": sum(
            check.status
            is ProbeCheckStatus.WARN
            for check in checks
        ),
        "checks_failed": sum(
            check.status
            is ProbeCheckStatus.FAIL
            for check in checks
        ),
    }

    safety = {
        "read_only": True,
        "runtime_modified": False,
        "gateway_instantiated": False,
        "titan_loaded": False,
        "retrieval_called": False,
        "cold_site_mutated": False,
        "adaptive_actions_applied": False,
        "opencode_modified": False,
        "mcp_modified": False,
    }

    return LiveProbeReport(
        probe_id=(
            probe_id
            or f"probe_{uuid.uuid4().hex}"
        ),
        runtime_root=str(root),
        status=_aggregate_status(checks),
        checks=checks,
        files=observations,
        counters=counters,
        safety=safety,
        generated_at=(
            generated_at
            or _utc_now_iso()
        ),
    )
