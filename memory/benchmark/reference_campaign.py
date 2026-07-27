from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from memory.benchmark.agent_multisession import (
    build_agent,
    run_agent_multisession_benchmark,
    write_agent_results,
)
from memory.benchmark.dataset_generator import (
    DatasetRequest,
    validate_dataset_directory,
    write_dataset,
)
from memory.benchmark.global_contracts import BenchmarkSize
from memory.benchmark.memory_pure_benchmark import (
    DeterministicLexicalEngine,
    MemoriXGatewayEngine,
    RetrievalEngine,
    run_pure_memory_benchmark,
    write_results,
)

CAMPAIGN_VERSION = "40.5.1"
SCHEMA_VERSION = 1
DEFAULT_SEEDS = (101, 202, 303)
OFFICIAL_SIZES = ("small", "medium")
PURE_METRICS = (
    "recall_at_1",
    "recall_at_5",
    "mean_reciprocal_rank",
    "forbidden_hit_rate",
    "exact_value_rate",
    "mean_retrieve_ms",
    "p95_retrieve_ms",
)
AGENT_METRICS = (
    "task_success_rate",
    "prior_information_reuse_rate",
    "forbidden_information_use_rate",
    "session_resume_success_rate",
    "exact_value_rate",
    "turn_count",
    "tool_call_count",
    "mean_response_ms",
    "p95_response_ms",
)


@dataclass(frozen=True, slots=True)
class CampaignRequest:
    size: str = "small"
    seeds: tuple[int, ...] = DEFAULT_SEEDS
    profile_count: int = 12
    project_count: int = 12
    top_k: int = 5

    def validate(self) -> None:
        if self.size not in OFFICIAL_SIZES:
            raise ValueError(
                "Reference campaign size must be small or medium."
            )
        if not self.seeds:
            raise ValueError("At least one seed is required.")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Duplicate seeds are not allowed.")
        if any(int(seed) < 0 for seed in self.seeds):
            raise ValueError("Seeds must be non-negative.")
        if self.profile_count < 1:
            raise ValueError("profile_count must be positive.")
        if self.project_count < 1:
            raise ValueError("project_count must be positive.")
        if self.top_k < 1:
            raise ValueError("top_k must be positive.")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8-sig")
    )
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            "Refusing to overwrite non-empty reference campaign directory: "
            f"{path}"
        )
    path.mkdir(parents=True, exist_ok=True)


def _summary(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise ValueError("Cannot summarize empty values.")
    count = len(values)
    mean_value = statistics.fmean(values)
    median_value = float(statistics.median(values))
    stdev_value = (
        statistics.stdev(values)
        if count > 1
        else 0.0
    )
    half_width = (
        1.96 * stdev_value / math.sqrt(count)
        if count > 1
        else 0.0
    )
    return {
        "count": count,
        "mean": round(mean_value, 6),
        "median": round(median_value, 6),
        "stdev": round(stdev_value, 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "ci95_low": round(
            mean_value - half_width,
            6,
        ),
        "ci95_high": round(
            mean_value + half_width,
            6,
        ),
    }


def _directory_size(path: Path) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file()
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _default_memory_engine(
    runtime_root: Path,
) -> RetrievalEngine:
    return MemoriXGatewayEngine(runtime_root)


def _run_pure_suite(
    *,
    dataset_root: Path,
    output_root: Path,
    engine_name: str,
    engine: RetrievalEngine,
    dataset_id: str,
    top_k: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    metrics, rows = run_pure_memory_benchmark(
        dataset_root,
        engine,
        top_k=top_k,
    )
    report_path = write_results(
        output_root,
        metrics,
        rows,
        engine_name=engine_name,
        dataset_id=dataset_id,
    )
    return {
        "report_path": str(report_path),
        "duration_ms": round(
            (time.perf_counter() - started) * 1000.0,
            3,
        ),
        "metrics": metrics.to_dict(),
    }


def _run_agent_suite(
    *,
    dataset_root: Path,
    output_root: Path,
    mode: str,
    backend: str,
    runtime_root: Path | None,
    dataset_id: str,
    top_k: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    agent = build_agent(
        mode=mode,
        backend=backend,
        runtime_root=runtime_root,
    )
    metrics, rows = run_agent_multisession_benchmark(
        dataset_root,
        agent,
        top_k=top_k,
    )
    report_path = write_agent_results(
        output_root,
        metrics,
        rows,
        mode=mode,
        backend=backend,
        dataset_id=dataset_id,
    )
    return {
        "report_path": str(report_path),
        "duration_ms": round(
            (time.perf_counter() - started) * 1000.0,
            3,
        ),
        "metrics": metrics.to_dict(),
    }


def run_reference_campaign(
    *,
    output_root: Path,
    configs_dir: Path,
    request: CampaignRequest,
    memory_engine_factory: Callable[
        [Path],
        RetrievalEngine,
    ] = _default_memory_engine,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    request.validate()
    _ensure_empty(output_root)

    datasets_root = output_root / "datasets"
    results_root = output_root / "results"
    runtimes_root = output_root / "runtimes"
    datasets_root.mkdir()
    results_root.mkdir()
    runtimes_root.mkdir()

    run_rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for seed in request.seeds:
        seed_name = f"seed-{seed:08d}"
        dataset_root = (
            datasets_root
            / seed_name
        )
        dataset_id = (
            f"reference-{request.size}-{seed}"
        )
        dataset_request = DatasetRequest(
            dataset_id=dataset_id,
            size=BenchmarkSize(request.size),
            seed=int(seed),
            profile_count=request.profile_count,
            project_count=request.project_count,
            include_queries=True,
        )

        artifact = write_dataset(
            dataset_request,
            configs_dir=configs_dir,
            output_dir=dataset_root,
        )
        validate_dataset_directory(dataset_root)

        seed_results = results_root / seed_name
        seed_runtimes = runtimes_root / seed_name
        seed_results.mkdir(parents=True)
        seed_runtimes.mkdir(parents=True)

        lexical_result = _run_pure_suite(
            dataset_root=dataset_root,
            output_root=seed_results / "pure_lexical",
            engine_name="lexical_control",
            engine=DeterministicLexicalEngine(),
            dataset_id=dataset_id,
            top_k=request.top_k,
        )
        run_rows.append(
            {
                "seed": seed,
                "size": request.size,
                "suite": "memory_pure",
                "mode": "lexical_control",
                "backend": "lexical",
                "record_count": artifact.record_count,
                "query_count": artifact.query_count,
                "runtime_size_bytes": 0,
                "duration_ms": lexical_result[
                    "duration_ms"
                ],
                **lexical_result["metrics"],
            }
        )

        pure_runtime = (
            seed_runtimes
            / "pure_memorix"
        )
        pure_memorix_result = _run_pure_suite(
            dataset_root=dataset_root,
            output_root=seed_results / "pure_memorix",
            engine_name="memorix_real",
            engine=memory_engine_factory(
                pure_runtime
            ),
            dataset_id=dataset_id,
            top_k=request.top_k,
        )
        run_rows.append(
            {
                "seed": seed,
                "size": request.size,
                "suite": "memory_pure",
                "mode": "memorix_core",
                "backend": "memorix",
                "record_count": artifact.record_count,
                "query_count": artifact.query_count,
                "runtime_size_bytes": (
                    _directory_size(
                        pure_runtime
                    )
                ),
                "duration_ms": pure_memorix_result[
                    "duration_ms"
                ],
                **pure_memorix_result["metrics"],
            }
        )

        no_memory_result = _run_agent_suite(
            dataset_root=dataset_root,
            output_root=seed_results / "agent_no_memory",
            mode="no_memory",
            backend="lexical",
            runtime_root=None,
            dataset_id=dataset_id,
            top_k=request.top_k,
        )
        run_rows.append(
            {
                "seed": seed,
                "size": request.size,
                "suite": "agent_multisession",
                "mode": "no_memory",
                "backend": "none",
                "record_count": artifact.record_count,
                "query_count": artifact.query_count,
                "runtime_size_bytes": 0,
                "duration_ms": no_memory_result[
                    "duration_ms"
                ],
                **no_memory_result["metrics"],
            }
        )

        agent_runtime = (
            seed_runtimes
            / "agent_memorix"
        )
        memorix_agent_result = _run_agent_suite(
            dataset_root=dataset_root,
            output_root=seed_results / "agent_memorix",
            mode="memorix_core",
            backend="memorix",
            runtime_root=agent_runtime,
            dataset_id=dataset_id,
            top_k=request.top_k,
        )
        run_rows.append(
            {
                "seed": seed,
                "size": request.size,
                "suite": "agent_multisession",
                "mode": "memorix_core",
                "backend": "memorix",
                "record_count": artifact.record_count,
                "query_count": artifact.query_count,
                "runtime_size_bytes": (
                    _directory_size(
                        agent_runtime
                    )
                ),
                "duration_ms": (
                    memorix_agent_result[
                        "duration_ms"
                    ]
                ),
                **memorix_agent_result["metrics"],
            }
        )

    aggregates: dict[str, Any] = {}

    for suite in (
        "memory_pure",
        "agent_multisession",
    ):
        suite_rows = [
            row
            for row in run_rows
            if row["suite"] == suite
        ]
        aggregates[suite] = {}

        modes = sorted(
            {
                str(row["mode"])
                for row in suite_rows
            }
        )
        metric_names = (
            PURE_METRICS
            if suite == "memory_pure"
            else AGENT_METRICS
        )

        for mode in modes:
            mode_rows = [
                row
                for row in suite_rows
                if row["mode"] == mode
            ]
            aggregates[suite][mode] = {
                metric: _summary(
                    [
                        float(row[metric])
                        for row in mode_rows
                    ]
                )
                for metric in metric_names
            }

    comparisons = {
        "memory_pure": {},
        "agent_multisession": {},
    }

    pure_modes = aggregates["memory_pure"]
    if (
        "memorix_core" in pure_modes
        and "lexical_control" in pure_modes
    ):
        comparisons["memory_pure"][
            "memorix_core_minus_lexical_control"
        ] = {
            metric: round(
                float(
                    pure_modes[
                        "memorix_core"
                    ][metric]["mean"]
                )
                - float(
                    pure_modes[
                        "lexical_control"
                    ][metric]["mean"]
                ),
                6,
            )
            for metric in PURE_METRICS
        }

    agent_modes = aggregates[
        "agent_multisession"
    ]
    if (
        "memorix_core" in agent_modes
        and "no_memory" in agent_modes
    ):
        comparisons["agent_multisession"][
            "memorix_core_minus_no_memory"
        ] = {
            metric: round(
                float(
                    agent_modes[
                        "memorix_core"
                    ][metric]["mean"]
                )
                - float(
                    agent_modes[
                        "no_memory"
                    ][metric]["mean"]
                ),
                6,
            )
            for metric in AGENT_METRICS
        }

    runs_jsonl = (
        output_root
        / "reference_runs.jsonl"
    )
    with runs_jsonl.open("wb") as handle:
        for row in run_rows:
            handle.write(_canonical_bytes(row))

    runs_csv = output_root / "reference_runs.csv"
    fieldnames = sorted(
        {
            key
            for row in run_rows
            for key in row
        }
    )
    with runs_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(run_rows)

    total_duration_ms = round(
        (
            time.perf_counter()
            - started
        )
        * 1000.0,
        3,
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "campaign_type": (
            "real_memorix_reference"
        ),
        "request": asdict(request),
        "run_count": len(run_rows),
        "dataset_count": len(
            request.seeds
        ),
        "real_memorix_run_count": sum(
            1
            for row in run_rows
            if row["backend"] == "memorix"
        ),
        "aggregates": aggregates,
        "comparisons": comparisons,
        "total_duration_ms": total_duration_ms,
        "artifacts": {
            "runs_jsonl": runs_jsonl.name,
            "runs_csv": runs_csv.name,
            "datasets_directory": (
                datasets_root.name
            ),
            "results_directory": (
                results_root.name
            ),
            "runtimes_directory": (
                runtimes_root.name
            ),
        },
    }

    report_path = (
        output_root
        / "reference_campaign_report.json"
    )
    _write_json(report_path, report)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "report_sha256": _sha256(
            report_path
        ),
        "runs_jsonl_sha256": _sha256(
            runs_jsonl
        ),
        "runs_csv_sha256": _sha256(
            runs_csv
        ),
        "output_size_bytes": (
            _directory_size(output_root)
        ),
    }
    _write_json(
        output_root
        / "reference_campaign_manifest.json",
        manifest,
    )

    if archive_path is not None:
        if archive_path.exists():
            raise FileExistsError(
                f"Archive already exists: {archive_path}"
            )
        archive_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        base_name = str(
            archive_path.with_suffix("")
        )
        created = shutil.make_archive(
            base_name,
            "zip",
            root_dir=output_root.parent,
            base_dir=output_root.name,
        )
        created_path = Path(created)
        if created_path != archive_path:
            if archive_path.exists():
                archive_path.unlink()
            created_path.replace(archive_path)

    return report


def validate_reference_campaign(
    report_path: Path,
) -> dict[str, Any]:
    report = _read_json(report_path)

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version.")
    if report.get("campaign_version") != CAMPAIGN_VERSION:
        raise ValueError("Invalid campaign_version.")
    if (
        report.get("campaign_type")
        != "real_memorix_reference"
    ):
        raise ValueError("Invalid campaign_type.")

    request = report.get("request")
    if not isinstance(request, dict):
        raise ValueError("Invalid request.")

    seeds = request.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("Invalid seeds.")

    expected_runs = len(seeds) * 4
    if int(report.get("run_count", -1)) != expected_runs:
        raise ValueError("Invalid run_count.")

    expected_real_runs = len(seeds) * 2
    if (
        int(
            report.get(
                "real_memorix_run_count",
                -1,
            )
        )
        != expected_real_runs
    ):
        raise ValueError(
            "Invalid real_memorix_run_count."
        )

    aggregates = report.get("aggregates")
    if not isinstance(aggregates, dict):
        raise ValueError("Invalid aggregates.")

    for suite in (
        "memory_pure",
        "agent_multisession",
    ):
        if suite not in aggregates:
            raise ValueError(
                f"Missing suite: {suite}"
            )

    return report
