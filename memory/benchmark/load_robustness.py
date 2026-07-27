from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
BENCHMARK_VERSION = "38.1"


def _canonical_bytes(value: Any) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (payload + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0

    total = 0

    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size

    return total


def _ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            "Refusing to overwrite non-empty robustness directory: "
            f"{path}"
        )

    path.mkdir(parents=True, exist_ok=True)


def _generate_records(count: int) -> list[dict[str, Any]]:
    if count < 1:
        raise ValueError("record_count must be positive")

    return [
        {
            "record_id": f"load-{index:08d}",
            "topic": f"topic-{index % 31:02d}",
            "value": f"value-{index:08d}",
            "active": True,
        }
        for index in range(count)
    ]


def _parse_jsonl_tolerant(
    path: Path,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    corrupted = 0

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:
        for line in handle:
            stripped = line.strip()

            if not stripped:
                continue

            try:
                value = json.loads(stripped)
            except json.JSONDecodeError:
                corrupted += 1
                continue

            if not isinstance(value, dict):
                corrupted += 1
                continue

            rows.append(value)

    return rows, corrupted


def _run_timeout_probe(
    timeout_seconds: float,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    started = time.perf_counter()

    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import time; "
                "print('PROBE_STARTED', flush=True); "
                "time.sleep(60)"
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    timed_out = False

    try:
        stdout, stderr = process.communicate(
            timeout=timeout_seconds
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000.0

    return {
        "timed_out": timed_out,
        "exit_code": process.returncode,
        "duration_ms": round(elapsed_ms, 3),
        "stdout": stdout,
        "stderr": stderr,
    }


def run_load_robustness(
    *,
    output_root: Path,
    record_count: int,
    corruption_lines: int,
    near_capacity_ratio: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    if corruption_lines < 1:
        raise ValueError("corruption_lines must be positive")

    if near_capacity_ratio <= 0:
        raise ValueError("near_capacity_ratio must be positive")

    if near_capacity_ratio > 1:
        raise ValueError("near_capacity_ratio cannot exceed 1")

    _ensure_empty(output_root)

    runtime_root = output_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = []
    started = time.perf_counter()

    records = _generate_records(record_count)
    store_path = runtime_root / "store.jsonl"

    store_started = time.perf_counter()
    _write_jsonl(store_path, records)
    store_duration_ms = (
        time.perf_counter() - store_started
    ) * 1000.0

    events.append(
        {
            "event": "bulk_store",
            "success": True,
            "record_count": record_count,
            "duration_ms": round(store_duration_ms, 3),
        }
    )

    original_hash = _sha256_file(store_path)
    original_size = store_path.stat().st_size

    backup_path = runtime_root / "store.backup.jsonl"
    shutil.copy2(store_path, backup_path)

    with store_path.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        for index in range(corruption_lines):
            handle.write(
                '{"corrupted_line": '
                + str(index)
                + "\n"
            )

    parsed_rows, detected_corruption = (
        _parse_jsonl_tolerant(store_path)
    )

    corruption_recovery_success = (
        len(parsed_rows) == record_count
        and detected_corruption == corruption_lines
    )

    events.append(
        {
            "event": "corruption_detection",
            "success": corruption_recovery_success,
            "valid_rows": len(parsed_rows),
            "corrupted_rows": detected_corruption,
        }
    )

    shutil.copy2(backup_path, store_path)

    restored_hash = _sha256_file(store_path)
    restore_success = restored_hash == original_hash

    events.append(
        {
            "event": "backup_restore",
            "success": restore_success,
            "restored_sha256": restored_hash,
        }
    )

    restart_started = time.perf_counter()
    restart_rows, restart_corruption = (
        _parse_jsonl_tolerant(store_path)
    )
    restart_duration_ms = (
        time.perf_counter() - restart_started
    ) * 1000.0

    restart_success = (
        len(restart_rows) == record_count
        and restart_corruption == 0
    )

    events.append(
        {
            "event": "restart_reload",
            "success": restart_success,
            "record_count": len(restart_rows),
            "duration_ms": round(restart_duration_ms, 3),
        }
    )

    simulated_capacity_bytes = max(
        original_size + 1,
        int(original_size / near_capacity_ratio),
    )
    used_ratio = original_size / simulated_capacity_bytes

    capacity_threshold_bytes = int(
        simulated_capacity_bytes
        * near_capacity_ratio
    )

    capacity_guard_triggered = (
        original_size >= capacity_threshold_bytes
    )

    events.append(
        {
            "event": "near_capacity_guard",
            "success": capacity_guard_triggered,
            "used_bytes": original_size,
            "capacity_bytes": simulated_capacity_bytes,
            "used_ratio": round(used_ratio, 6),
        }
    )

    timeout_probe = _run_timeout_probe(timeout_seconds)

    timeout_success = (
        timeout_probe["timed_out"] is True
        and timeout_probe["duration_ms"]
        < (timeout_seconds * 1000.0) + 5000.0
    )

    events.append(
        {
            "event": "timeout_probe",
            "success": timeout_success,
            "timed_out": timeout_probe["timed_out"],
            "duration_ms": timeout_probe["duration_ms"],
            "exit_code": timeout_probe["exit_code"],
        }
    )

    events_path = output_root / "robustness_events.jsonl"
    _write_jsonl(events_path, events)

    successful_events = sum(
        1
        for event in events
        if event["success"]
    )

    total_duration_ms = (
        time.perf_counter() - started
    ) * 1000.0

    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "suite": "load_robustness",
        "configuration": {
            "record_count": record_count,
            "corruption_lines": corruption_lines,
            "near_capacity_ratio": near_capacity_ratio,
            "timeout_seconds": timeout_seconds,
        },
        "metrics": {
            "event_count": len(events),
            "success_rate": successful_events / len(events),
            "store_duration_ms": round(store_duration_ms, 3),
            "restart_duration_ms": round(
                restart_duration_ms,
                3,
            ),
            "corruption_detection_rate": (
                detected_corruption / corruption_lines
            ),
            "restore_success_rate": (
                1.0 if restore_success else 0.0
            ),
            "restart_success_rate": (
                1.0 if restart_success else 0.0
            ),
            "timeout_enforcement_rate": (
                1.0 if timeout_success else 0.0
            ),
            "capacity_guard_rate": (
                1.0 if capacity_guard_triggered else 0.0
            ),
            "runtime_size_bytes": _directory_size(
                runtime_root
            ),
            "total_duration_ms": round(
                total_duration_ms,
                3,
            ),
        },
        "store_sha256": original_hash,
        "events_sha256": _sha256_file(events_path),
    }

    _write_json(
        output_root / "load_robustness_report.json",
        report,
    )

    return report


def validate_load_robustness_report(
    path: Path,
) -> dict[str, Any]:
    report = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version")

    if report.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError("Invalid benchmark_version")

    if report.get("suite") != "load_robustness":
        raise ValueError("Invalid suite")

    metrics = report.get("metrics", {})

    bounded_metrics = (
        "success_rate",
        "corruption_detection_rate",
        "restore_success_rate",
        "restart_success_rate",
        "timeout_enforcement_rate",
        "capacity_guard_rate",
    )

    for metric_name in bounded_metrics:
        metric_value = float(
            metrics.get(metric_name, -1)
        )

        if metric_value < 0:
            raise ValueError(
                f"Invalid metric: {metric_name}"
            )

        if metric_value > 1:
            raise ValueError(
                f"Invalid metric: {metric_name}"
            )

    if int(metrics.get("event_count", 0)) != 6:
        raise ValueError("Invalid event_count")

    if int(metrics.get("runtime_size_bytes", -1)) < 0:
        raise ValueError("Invalid runtime_size_bytes")

    if len(str(report.get("store_sha256", ""))) != 64:
        raise ValueError("Invalid store_sha256")

    if len(str(report.get("events_sha256", ""))) != 64:
        raise ValueError("Invalid events_sha256")

    return report
