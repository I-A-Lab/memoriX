#!/usr/bin/env python3
"""memoriX Full Benchmark Runner.

Usage:
    py -3.13 benchmarks/run_full_benchmark.py
    py -3.13 benchmarks/run_full_benchmark.py --model gemma2:2b
    py -3.13 benchmarks/run_full_benchmark.py --seeds 42 101 202
    py -3.13 benchmarks/run_full_benchmark.py --families f01 f02 f03
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

try:
    from benchmarks.orchestrator.direct_llm_runner import list_available_families
except ImportError:
    list_available_families = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run memoriX benchmark and generate reports."
    )
    parser.add_argument(
        "--model", default="qwen2.5:3b",
        help="Ollama model name (default: qwen2.5:3b)"
    )
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[42, 101],
        help="Random seeds (default: 42 101)"
    )
    parser.add_argument(
        "--families", nargs="*",
        help="Family IDs to run (default: all 32)"
    )
    parser.add_argument(
        "--output", type=Path,
        default=REPO_ROOT / ".benchmarks" / "full_run",
        help="Output directory"
    )
    parser.add_argument(
        "--report-only", action="store_true",
        help="Skip benchmark, regenerate reports from existing raw_results.json"
    )
    return parser.parse_args()


def run_benchmark(args: argparse.Namespace) -> None:
    from benchmarks.orchestrator.llm_backends import OllamaBackend
    from benchmarks.orchestrator.orchestrator import BenchmarkOrchestrator
    from benchmarks.orchestrator.data_models import CampaignManifest

    print(f"Model:    {args.model}")
    print(f"Seeds:    {args.seeds}")
    print(f"Families: {args.families or 'all 32'}")
    print(f"Output:   {args.output}")
    print()

    backend = OllamaBackend(model=args.model)
    if not backend.is_available():
        print(f"ERROR: Ollama model '{args.model}' is not available.")
        print(f"Available models: {backend.list_models()}")
        sys.exit(1)

    orchestrator = BenchmarkOrchestrator(
        output_dir=args.output,
        dry_run=False,
        backend=backend,
    )

    manifest = CampaignManifest(
        campaign_id="full-benchmark",
        profile_name="standard",
        seeds=args.seeds,
        total_pairs=len(args.seeds),
        created_by="research-doc",
    )

    # Estimate total runs
    if args.families:
        family_list = args.families
    elif list_available_families is not None:
        family_list = list_available_families()
    else:
        family_list = [f"f{i:02d}" for i in range(1, 33)]
    total_expected = len(family_list) * len(args.seeds)  # pairs (each pair = 2 modes)
    print(f"Estimated runs: {total_expected}")
    print(f"Starting benchmark... (first call may take 30-60s for model warm-up)")
    print()
    sys.stdout.flush()

    # Warm up the model
    print("Warming up model (loading into memory)...", flush=True)
    from benchmarks.orchestrator.direct_llm_runner import DirectRunRequest, run_direct
    warmup = run_direct(DirectRunRequest(
        family_id="f01_exact_key_recall",
        seed=999,
        mode="no_memory",
        backend=backend,
    ))
    if warmup.error:
        print(f"WARNING: Warm-up failed: {warmup.error}")
    else:
        print(f"Model ready. First call took {warmup.duration_ms:.0f}ms")
    print()

    start = time.perf_counter()

    # Run with progress tracking
    from benchmarks.orchestrator.direct_llm_runner import run_direct_pair

    results = []
    run_count = 0

    for fam in family_list:
        for seed in args.seeds:
            # Run both modes at once
            run_count += 1
            print(f"  [{run_count:3d}/{len(family_list) * len(args.seeds)}] {fam} | seed={seed} ... ", end="", flush=True)

            try:
                no_mem, mem_core = run_direct_pair(
                    family_id=fam,
                    seed=seed,
                    backend=backend,
                )
                
                # Report both results
                nm_status = "PASS" if no_mem.passed else "FAIL"
                mc_status = "PASS" if mem_core.passed else "FAIL"
                print(f"no_memory={nm_status} ({no_mem.duration_ms:.0f}ms) | memorix={mc_status} ({mem_core.duration_ms:.0f}ms)")

                # Convert both to RunResult
                from benchmarks.orchestrator.data_models import RunResult
                
                for mode_label, chosen in [("no_memory", no_mem), ("memorix_core", mem_core)]:
                    results.append(RunResult(
                        schema_version=1,
                        run_id=f"bench-{fam}-seed{seed:08d}-{mode_label[:1]}",
                        campaign_id="full-benchmark",
                        family=fam,
                        mode="A" if mode_label == "no_memory" else "B",
                        seed=seed,
                        pair_index=0 if mode_label == "no_memory" else 1,
                        status="passed" if chosen.passed else "failed",
                        failure_category="PASS" if chosen.passed else "FAIL",
                        precision=chosen.passed_case_count / max(chosen.case_count, 1),
                        recall=chosen.passed_case_count / max(chosen.case_count, 1),
                        f1=chosen.passed_case_count / max(chosen.case_count, 1),
                        latency_ms=chosen.duration_ms,
                        prompt_tokens=chosen.prompt_tokens,
                        completion_tokens=chosen.completion_tokens,
                        total_tokens=chosen.total_tokens,
                        estimated_cost_usd=0.0,
                        rss_bytes=0,
                        cpu_percent=0.0,
                        duration_ms=chosen.duration_ms,
                        artifacts_path="",
                        created_at_utc="",
                        dry_run=False,
                    ))
            except Exception as e:
                print(f"ERROR ({e})")

    elapsed = time.perf_counter() - start

    # Save raw results
    import json
    raw_path = args.output / "full-benchmark"
    raw_path.mkdir(parents=True, exist_ok=True)
    raw_file = raw_path / "raw_results.json"
    raw_file.write_text(
        json.dumps([r.to_dict() for r in results], indent=2),
        encoding="utf-8",
    )
    print(f"Raw results saved to: {raw_file}")

    passed = sum(1 for r in results if r.status == "passed")
    total = len(results)

    print()
    print("=" * 60)
    print(f"BENCHMARK COMPLETE")
    print(f"=" * 60)
    print(f"Total runs:   {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {total - passed}")
    print(f"Pass rate:    {passed / total:.1%}")
    print(f"Duration:     {elapsed:.1f}s")
    print(f"Avg per run:  {elapsed / total:.1f}s")
    print()

    # Per-family breakdown
    from collections import defaultdict
    family_stats = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        family_stats[r.family]["total"] += 1
        if r.status == "passed":
            family_stats[r.family]["passed"] += 1

    print("Per-family:")
    for fam in sorted(family_stats):
        s = family_stats[fam]
        rate = s["passed"] / s["total"]
        bar = "#" * int(rate * 20)
        print(f"  {fam:35s} {s['passed']}/{s['total']} ({rate:3.0%}) {bar}")

    # Per-mode breakdown
    mode_stats = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        mode_stats[r.mode]["total"] += 1
        if r.status == "passed":
            mode_stats[r.mode]["passed"] += 1

    print()
    print("Per-mode:")
    for mode in sorted(mode_stats):
        s = mode_stats[mode]
        rate = s["passed"] / s["total"]
        label = "no_memory  " if mode == "A" else "memorix_core"
        print(f"  {label} {s['passed']}/{s['total']} ({rate:3.0%})")


def generate_reports(args: argparse.Namespace) -> None:
    from benchmarks.orchestrator.orchestrator import BenchmarkOrchestrator
    from benchmarks.reporting.report_generator import ReportGenerator
    from benchmarks.reporting.figures import FigureGenerator

    campaign_dir = args.output / "full-benchmark"
    raw_path = campaign_dir / "raw_results.json"

    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run benchmark first.")
        sys.exit(1)

    print("Generating reports...")

    # Load raw results for aggregation
    import json
    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    families = sorted(set(r.get("family", "") for r in raw_data))

    # We need aggregate reports. Build them from raw data.
    from collections import defaultdict
    from benchmarks.orchestrator.data_models import AggregateReport

    family_groups = defaultdict(list)
    for r in raw_data:
        family_groups[r["family"]].append(r)

    aggregate_reports = []
    for fam, runs in sorted(family_groups.items()):
        precisions = [r.get("precision", 0) for r in runs]
        latencies = [r.get("latency_ms", 0) for r in runs]
        passed = sum(1 for r in runs if r.get("status") == "passed")
        total = len(runs)

        aggregate_reports.append(AggregateReport(
            schema_version=1,
            campaign_id="full-benchmark",
            family=fam,
            suite="standard",
            precision=sum(precisions) / max(len(precisions), 1),
            recall=sum(precisions) / max(len(precisions), 1),
            f1=sum(precisions) / max(len(precisions), 1),
            pass_rate=passed / max(total, 1),
            total_runs=total,
            failed_runs=total - passed,
            median_latency=sorted(latencies)[len(latencies) // 2] if latencies else 0,
            p95_latency=sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        ))

    gen = ReportGenerator(args.output)

    # Markdown
    md_path = gen.generate("full-benchmark", "standard", families, aggregate_reports)
    print(f"  [MD]   {md_path}")

    # DOCX
    try:
        docx_path = gen.generate_docx("full-benchmark", "standard", families, aggregate_reports)
        print(f"  [DOCX] {docx_path}")
    except Exception as e:
        print(f"  [DOCX] Skipped: {e}")

    # Figures
    try:
        figs = FigureGenerator(args.output)
        figs.generate_all("full-benchmark", aggregate_reports, raw_data)
        print(f"  [PNG]  Figures saved to {args.output / 'full-benchmark' / 'figures'}")
    except Exception as e:
        print(f"  [PNG]  Skipped: {e}")

    print()
    print("All reports generated.")


def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("  memoriX FULL BENCHMARK")
    print("=" * 60)
    print()

    if not args.report_only:
        run_benchmark(args)
        print()

    generate_reports(args)


if __name__ == "__main__":
    main()
