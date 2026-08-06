from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

from memory.benchmark.sdlc_benchmark import (
    run_sdlc_benchmark,
    validate_sdlc_report,
)

SCHEMA_VERSION = 1
ORCHESTRATOR_VERSION = "39.1"
VALID_MODES = ("no_memory", "memorix_core")
SUPPORTED_SUITE = "sdlc"


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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")

    return value


def _ensure_initial_output(path: Path, resume: bool) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    if not path.is_dir():
        raise ValueError(
            f"Output path is not a directory: {path}"
        )

    has_entries = any(path.iterdir())

    if has_entries and not resume:
        raise FileExistsError(
            "Refusing to overwrite non-empty multiseed directory: "
            f"{path}"
        )


def _validate_seeds(seeds: list[int]) -> list[int]:
    if not seeds:
        raise ValueError("At least one seed is required")

    normalized = [int(seed) for seed in seeds]

    if len(set(normalized)) != len(normalized):
        raise ValueError("Duplicate seeds are not allowed")

    for seed in normalized:
        if seed < 0:
            raise ValueError("Seeds must be non-negative")

    return normalized


def _summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise ValueError("Cannot summarize an empty series")

    count = len(values)
    mean_value = statistics.fmean(values)
    median_value = statistics.median(values)

    if count > 1:
        stdev_value = statistics.stdev(values)
    else:
        stdev_value = 0.0

    ci95_half_width = (
        1.96 * stdev_value / math.sqrt(count)
        if count > 1
        else 0.0
    )

    return {
        "count": count,
        "mean": round(mean_value, 6),
        "median": round(float(median_value), 6),
        "stdev": round(stdev_value, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "ci95_low": round(
            mean_value - ci95_half_width,
            6,
        ),
        "ci95_high": round(
            mean_value + ci95_half_width,
            6,
        ),
    }


def _run_directory(
    output_root: Path,
    mode: str,
    seed: int,
) -> Path:
    return (
        output_root
        / "runs"
        / mode
        / f"seed-{seed:08d}"
    )


def _load_completed_run(
    run_root: Path,
    expected_mode: str,
    expected_seed: int,
) -> dict[str, Any] | None:
    report_path = run_root / "sdlc_report.json"
    metadata_path = run_root / "run_metadata.json"

    if not report_path.is_file():
        return None

    if not metadata_path.is_file():
        return None

    report = validate_sdlc_report(report_path)
    metadata = _read_json(metadata_path)

    if report.get("mode") != expected_mode:
        raise ValueError(
            f"Unexpected mode in resumed report: {report_path}"
        )

    if int(metadata.get("seed", -1)) != expected_seed:
        raise ValueError(
            f"Unexpected seed in resumed metadata: {metadata_path}"
        )

    return report


def run_multiseed_orchestrator(
    *,
    output_root: Path,
    seeds: list[int],
    modes: list[str] | None = None,
    suite: str = SUPPORTED_SUITE,
    resume: bool = False,
) -> dict[str, Any]:
    normalized_seeds = _validate_seeds(seeds)
    selected_modes = list(modes or VALID_MODES)

    if suite != SUPPORTED_SUITE:
        raise ValueError(f"Unsupported suite: {suite}")

    if not selected_modes:
        raise ValueError("At least one mode is required")

    if len(set(selected_modes)) != len(selected_modes):
        raise ValueError("Duplicate modes are not allowed")

    for mode in selected_modes:
        if mode not in VALID_MODES:
            raise ValueError(f"Unsupported mode: {mode}")

    _ensure_initial_output(output_root, resume)

    run_rows: list[dict[str, Any]] = []
    completed = 0
    resumed = 0

    for mode in selected_modes:
        for seed in normalized_seeds:
            run_root = _run_directory(
                output_root,
                mode,
                seed,
            )

            existing_report = None

            if resume:
                existing_report = _load_completed_run(
                    run_root,
                    mode,
                    seed,
                )

            if existing_report is not None:
                report = existing_report
                resumed += 1
            else:
                if run_root.exists():
                    for item in sorted(
                        run_root.rglob("*"),
                        reverse=True,
                    ):
                        if item.is_file() or item.is_symlink():
                            item.unlink()
                        elif item.is_dir():
                            item.rmdir()

                run_root.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                report = run_sdlc_benchmark(
                    output_root=run_root,
                    mode=mode,
                    backend="deterministic",
                )

                _write_json(
                    run_root / "run_metadata.json",
                    {
                        "schema_version": 1,
                        "suite": suite,
                        "mode": mode,
                        "seed": seed,
                    },
                )
                completed += 1

            metrics = report["metrics"]

            run_rows.append(
                {
                    "suite": suite,
                    "mode": mode,
                    "seed": seed,
                    "task_completion_rate": float(
                        metrics["task_completion_rate"]
                    ),
                    "test_pass_rate": float(
                        metrics["test_pass_rate"]
                    ),
                    "decision_reuse_accuracy": float(
                        metrics["decision_reuse_accuracy"]
                    ),
                    "regression_count": float(
                        metrics["regression_count"]
                    ),
                    "session_resume_success_rate": float(
                        metrics[
                            "session_resume_success_rate"
                        ]
                    ),
                    "total_duration_ms": float(
                        metrics["total_duration_ms"]
                    ),
                }
            )

    metric_names = (
        "task_completion_rate",
        "test_pass_rate",
        "decision_reuse_accuracy",
        "regression_count",
        "session_resume_success_rate",
        "total_duration_ms",
    )

    by_mode: dict[str, Any] = {}

    for mode in selected_modes:
        mode_rows = [
            row
            for row in run_rows
            if row["mode"] == mode
        ]

        by_mode[mode] = {
            metric_name: _summary(
                [
                    float(row[metric_name])
                    for row in mode_rows
                ]
            )
            for metric_name in metric_names
        }

    comparisons: dict[str, Any] = {}

    if (
        "no_memory" in by_mode
        and "memorix_core" in by_mode
    ):
        comparisons["memorix_core_minus_no_memory"] = {
            metric_name: round(
                float(
                    by_mode["memorix_core"][
                        metric_name
                    ]["mean"]
                )
                - float(
                    by_mode["no_memory"][
                        metric_name
                    ]["mean"]
                ),
                6,
            )
            for metric_name in metric_names
        }

    report = {
        "schema_version": SCHEMA_VERSION,
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "suite": suite,
        "seeds": normalized_seeds,
        "modes": selected_modes,
        "run_count": len(run_rows),
        "completed_run_count": completed,
        "resumed_run_count": resumed,
        "aggregates": by_mode,
        "comparisons": comparisons,
    }

    _write_json(
        output_root / "multiseed_report.json",
        report,
    )

    with (
        output_root / "multiseed_runs.jsonl"
    ).open("wb") as handle:
        for row in run_rows:
            handle.write(_canonical_bytes(row))

    return report


def validate_multiseed_report(
    path: Path,
) -> dict[str, Any]:
    report = _read_json(path)

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version")

    if (
        report.get("orchestrator_version")
        != ORCHESTRATOR_VERSION
    ):
        raise ValueError("Invalid orchestrator_version")

    if report.get("suite") != SUPPORTED_SUITE:
        raise ValueError("Invalid suite")

    seeds = report.get("seeds")

    if not isinstance(seeds, list) or not seeds:
        raise ValueError("Invalid seeds")

    modes = report.get("modes")

    if not isinstance(modes, list) or not modes:
        raise ValueError("Invalid modes")

    expected_run_count = len(seeds) * len(modes)

    if int(report.get("run_count", -1)) != expected_run_count:
        raise ValueError("Invalid run_count")

    aggregates = report.get("aggregates")

    if not isinstance(aggregates, dict):
        raise ValueError("Invalid aggregates")

    for mode in modes:
        if mode not in aggregates:
            raise ValueError(
                f"Missing aggregate for mode: {mode}"
            )

        for metric_name, summary in aggregates[mode].items():
            if not isinstance(summary, dict):
                raise ValueError(
                    f"Invalid summary: {mode}/{metric_name}"
                )

            if int(summary.get("count", -1)) != len(seeds):
                raise ValueError(
                    f"Invalid count: {mode}/{metric_name}"
                )

            low = float(summary.get("ci95_low", 0))
            high = float(summary.get("ci95_high", 0))

            if low > high:
                raise ValueError(
                    f"Invalid confidence interval: "
                    f"{mode}/{metric_name}"
                )

    return report
