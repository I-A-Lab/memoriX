"""Run the official memoriX multi-session agent benchmark at x5 scale.

5 seeds x medium size = 5000 queries per condition (x5 of the medium
reference scale), comparing no_memory vs memorix_core, and aggregating
everything into one consolidated report (JSON + CSV + console table).

Standard library only. The memoriX runtime root and all output artifacts
live OUTSIDE the repository (C:\\GitHub\\memoriX) so that
MemoriXGatewayEngine validation never fails on in-repo runtimes.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(r"C:\GitHub\memoriX")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from memory.benchmark.agent_multisession import (  # noqa: E402
    build_agent,
    run_agent_multisession_benchmark,
    write_agent_results,
)
from memory.benchmark.dataset_generator import (  # noqa: E402
    DatasetRequest,
    validate_dataset_directory,
    write_dataset,
)
from memory.benchmark.global_contracts import BenchmarkSize  # noqa: E402

CONFIGS_DIR = REPO_ROOT / "benchmarks" / "memorix_vs_no_memory" / "configs"
RUNTIME_ROOT = Path(r"C:\Users\anttn\AppData\Local\Temp\opencode\memorix-agent-runtime")
OUTPUT_ROOT = Path(r"C:\Users\anttn\AppData\Local\Temp\opencode\memorix-agent-x5")
SEEDS = [101, 202, 303, 404, 505]  # 5 seeds = x5 of the reference campaign
SIZE = "medium"  # 1000 queries per seed => 5000 per condition
TOP_K = 5
MODES = [("no_memory", "lexical", None), ("memorix_core", "memorix", RUNTIME_ROOT)]

METRIC_FIELDS = (
    "query_count",
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

MODE_LABELS = {"no_memory": "No memory", "memorix_core": "memorix_core"}


def _empty_metrics() -> dict:
    return {
        "query_count": 0,
        "task_success_rate": 0.0,
        "prior_information_reuse_rate": 0.0,
        "forbidden_information_use_rate": 0.0,
        "session_resume_success_rate": 0.0,
        "exact_value_rate": 0.0,
        "turn_count": 0,
        "tool_call_count": 0,
        "mean_response_ms": 0.0,
        "p95_response_ms": 0.0,
    }


def _ensure_dataset(dataset_dir: Path, seed: int) -> dict:
    """Generate (or validate an existing) deterministic dataset for one seed."""
    if (dataset_dir / "dataset_manifest.json").is_file():
        validate_dataset_directory(dataset_dir)
    else:
        request = DatasetRequest(
            dataset_id=f"agent-x5-medium-{seed}",
            size=BenchmarkSize(SIZE),
            seed=seed,
            profile_count=12,
            project_count=12,
            include_queries=True,
        )
        write_dataset(request, configs_dir=CONFIGS_DIR, output_dir=dataset_dir)
        validate_dataset_directory(dataset_dir)
    return json.loads(
        (dataset_dir / "dataset_manifest.json").read_text(encoding="utf-8-sig")
    )


def _run_seed_mode(
    dataset_dir: Path,
    seed: int,
    mode: str,
    backend: str,
    runtime: Path | None,
    dataset_id: str,
) -> dict:
    """Run one seed x mode condition, resuming from a cached report if present."""
    run_root = OUTPUT_ROOT / "results" / f"seed-{seed:08d}" / mode
    report_path = run_root / "agent_report.json"
    if report_path.is_file():
        payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
        metrics = dict(payload["metrics"])
        print(
            f"[seed {seed}] {mode}/{backend}: {metrics['task_success_rate']:.1%} "
            f"success ({metrics['query_count']} queries) [cached]"
        )
        return metrics

    runtime_root = None if runtime is None else runtime / f"seed-{seed:08d}"
    if runtime_root is not None:
        runtime_root.mkdir(parents=True, exist_ok=True)

    agent = build_agent(mode=mode, backend=backend, runtime_root=runtime_root)
    metrics, rows = run_agent_multisession_benchmark(dataset_dir, agent, top_k=TOP_K)
    write_agent_results(
        run_root,
        metrics,
        rows,
        mode=mode,
        backend=backend,
        dataset_id=dataset_id,
    )
    metrics_dict = metrics.to_dict()
    print(
        f"[seed {seed}] {mode}/{backend}: {metrics_dict['task_success_rate']:.1%} "
        f"success ({metrics_dict['query_count']} queries)"
    )
    return metrics_dict


def _aggregate_per_mode(per_seed: list[dict]) -> dict:
    """Aggregate one mode across seeds; rates and latencies weighted by query_count."""
    if not per_seed:
        return _empty_metrics()
    total_queries = sum(int(item["query_count"]) for item in per_seed)

    def weighted(name: str) -> float:
        return (
            sum(
                float(item[name]) * int(item["query_count"]) for item in per_seed
            )
            / total_queries
        )

    return {
        "query_count": total_queries,
        "task_success_rate": weighted("task_success_rate"),
        "prior_information_reuse_rate": weighted("prior_information_reuse_rate"),
        "forbidden_information_use_rate": weighted("forbidden_information_use_rate"),
        "session_resume_success_rate": weighted("session_resume_success_rate"),
        "exact_value_rate": weighted("exact_value_rate"),
        # Each run reports turn_count = query_count + 2; drop the 2 base turns
        # per run, then re-add one base turn for the aggregated campaign.
        "turn_count": (
            sum(int(item["turn_count"]) for item in per_seed)
            - 2 * len(per_seed)
            + 2
        ),
        "tool_call_count": sum(int(item["tool_call_count"]) for item in per_seed),
        "mean_response_ms": weighted("mean_response_ms"),
        "p95_response_ms": max(float(item["p95_response_ms"]) for item in per_seed),
    }


def _write_summary(summaries: dict) -> None:
    payload = {
        "benchmark": "agent_multisession_x5",
        "size": SIZE,
        "top_k": TOP_K,
        "seeds": SEEDS,
        "expected_queries_per_condition": len(SEEDS) * 1000,
        "modes": {
            mode: {"aggregate": info["aggregate"], "per_seed": info["per_seed"]}
            for mode, info in summaries.items()
        },
    }
    summary_path = OUTPUT_ROOT / "agent_x5_summary.json"
    summary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_csv(summaries: dict) -> None:
    fieldnames = ["mode", *METRIC_FIELDS]
    csv_path = OUTPUT_ROOT / "agent_x5_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for mode, info in summaries.items():
            for seed_key in sorted(info["per_seed"], key=int):
                metrics = info["per_seed"][seed_key]
                if "error" in metrics:
                    continue
                writer.writerow(
                    {"mode": f"{mode}_seed_{seed_key}", **{k: metrics[k] for k in METRIC_FIELDS}}
                )
            writer.writerow(
                {"mode": mode, **{k: info["aggregate"][k] for k in METRIC_FIELDS}}
            )


def _print_final_table(summaries: dict) -> None:
    bar = "=" * 64
    no_memory = summaries["no_memory"]["aggregate"]
    memorix = summaries["memorix_core"]["aggregate"]
    delta_pp = (memorix["task_success_rate"] - no_memory["task_success_rate"]) * 100
    sign = "+" if delta_pp >= 0 else ""
    print(bar)
    print(
        f"MULTI-AGENT BENCHMARK x5 COMPLETE "
        f"({len(SEEDS)} seeds x {SIZE} = {len(SEEDS) * 1000} queries/condition)"
    )
    print(
        f"{MODE_LABELS['no_memory'] + ':':<15}"
        f"rate {no_memory['task_success_rate']:.1%} ({no_memory['query_count']} queries)"
    )
    print(
        f"{MODE_LABELS['memorix_core'] + ':':<15}"
        f"rate {memorix['task_success_rate']:.1%} ({memorix['query_count']} queries)"
    )
    print(f"{'Delta:':<15}{sign}{delta_pp:.1f} pp")
    print(bar)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)

    all_results: dict[str, dict[str, dict]] = {mode: {} for mode, _, _ in MODES}

    for seed in SEEDS:
        (RUNTIME_ROOT / f"seed-{seed:08d}").mkdir(parents=True, exist_ok=True)
        dataset_dir = OUTPUT_ROOT / "datasets" / f"seed-{seed:08d}"
        manifest = _ensure_dataset(dataset_dir, seed)
        dataset_id = str(manifest["dataset_id"])

        for mode, backend, runtime in MODES:
            try:
                metrics = _run_seed_mode(
                    dataset_dir, seed, mode, backend, runtime, dataset_id
                )
            except Exception as exc:  # keep the campaign alive; record the failure
                print(f"[seed {seed}] {mode}/{backend}: FAILED - {exc!r}")
                all_results[mode][str(seed)] = {"error": repr(exc)}
                continue
            all_results[mode][str(seed)] = metrics

    summaries: dict = {}
    for mode, _, _ in MODES:
        per_seed = {
            key: value
            for key, value in all_results[mode].items()
            if "error" not in value
        }
        summaries[mode] = {
            "aggregate": _aggregate_per_mode(list(per_seed.values())),
            "per_seed": per_seed,
        }

    _write_summary(summaries)
    _write_csv(summaries)
    _print_final_table(summaries)


if __name__ == "__main__":
    main()
