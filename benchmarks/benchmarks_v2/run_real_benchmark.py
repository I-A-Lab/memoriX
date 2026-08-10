#!/usr/bin/env python3
"""Run the real memoriX benchmark using OpenCode CLI + Ollama.

This uses the actual OpenCode CLI with the real memoriX memory system,
matching the methodology from the master benchmark report.

Prerequisites:
- Ollama running with a model pulled (e.g., qwen2.5:3b)
- bun installed and available on PATH

Usage:
    py -3.13 benchmarks/run_real_benchmark.py
    py -3.13 benchmarks/run_real_benchmark.py --model qwen2.5:3b --seeds 42 101 202
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Task kinds from the real runner
TASK_KINDS = (
    "csv_delimiter",
    "username_separator",
    "retry_schedule",
    "date_format",
    "cache_key",
    "page_size",
    "boolean_tokens",
    "filename_policy",
)

# Family to kind mapping
FAMILY_TO_KIND = {
    "f01_exact_key_recall": "csv_delimiter",
    "f02_semantic_retrieval": "username_separator",
    "f03_distractor_robustness": "retry_schedule",
    "f04_multi_hop_reasoning": "date_format",
    "f05_temporal_decay": "cache_key",
    "f06_contextual_disambiguation": "page_size",
    "f07_adversarial_injection": "boolean_tokens",
    "f08_cross_session_leak": "filename_policy",
    "f09_privacy_isolation": "csv_delimiter",
    "f10_consolidation_quality": "username_separator",
    "f11_forgetting_curve": "retry_schedule",
    "f12_capacity_management": "date_format",
    "f13_search_precision": "cache_key",
    "f14_search_recall": "page_size",
    "f15_ranking_relevance": "boolean_tokens",
    "f16_query_expansion": "filename_policy",
    "f17_partial_match": "csv_delimiter",
    "f18_noise_tolerance": "username_separator",
    "f19_schema_evolution": "retry_schedule",
    "f20_version_awareness": "date_format",
    "f21_concurrent_access": "cache_key",
    "f22_migration_safety": "page_size",
    "f23_api_conformance": "boolean_tokens",
    "f24_sdk_compatibility": "filename_policy",
    "f25_performance_baseline": "csv_delimiter",
    "f26_latency_budget": "username_separator",
    "f27_memory_footprint": "retry_schedule",
    "f28_streaming_integrity": "date_format",
    "f29_end_to_end_smoke": "cache_key",
    "f30_reproducibility": "page_size",
    "f31_determinism_check": "boolean_tokens",
    "f32_golden_output": "filename_policy",
}


def stable_token(seed: int, kind: str, suffix: str) -> str:
    return hashlib.sha256(f"{seed}|{kind}|{suffix}".encode()).hexdigest()[:12]


def build_task(kind: str, seed: int) -> dict[str, Any]:
    """Build a task spec matching the real runner's format."""
    rng = random.Random(f"{seed}|{kind}|40.7")
    token = stable_token(seed, kind, "task")
    project_id = f"bench-{kind}-{seed}-{token[:6]}"
    feature_id = f"feature-{token[6:]}"

    if kind == "csv_delimiter":
        delimiter = rng.choice([";", "|", "\t"])
        expected = {"delimiter": delimiter}
        decision = f"For feature {feature_id}, serialize table cells with delimiter {delimiter!r}."
        scaffold = "from __future__ import annotations\n\ndef serialize_rows(rows: list[list[object]]) -> str:\n    raise NotImplementedError\n"
        behavior = f"Implement serialize_rows(rows). Join cells with {delimiter!r}, rows with LF, no trailing LF."
    elif kind == "username_separator":
        separator = rng.choice(["-", "_", "."])
        expected = {"separator": separator}
        decision = f"For feature {feature_id}, normalized usernames use {separator!r}."
        scaffold = "from __future__ import annotations\n\ndef normalize_username(value: str) -> str:\n    raise NotImplementedError\n"
        behavior = f"Implement normalize_username(value). Trim, lowercase, replace whitespace with {separator!r}."
    elif kind == "retry_schedule":
        base = rng.choice([0.1, 0.25, 0.5])
        factor = rng.choice([1.5, 2.0, 3.0])
        expected = {"base": base, "factor": factor}
        decision = f"For feature {feature_id}, retry starts at {base}s, multiply by {factor}."
        scaffold = "from __future__ import annotations\n\ndef retry_delays(attempts: int) -> list[float]:\n    raise NotImplementedError\n"
        behavior = f"Implement retry_delays(attempts). Start at {base}, multiply by {factor}, round to 3 decimals."
    elif kind == "date_format":
        fmt = rng.choice(["%d/%m/%Y", "%Y-%m-%d", "%m.%d.%Y"])
        expected = {"format": fmt}
        decision = f"For feature {feature_id}, use date format {fmt!r}."
        scaffold = "from __future__ import annotations\nfrom datetime import date\n\ndef format_date(value: date) -> str:\n    raise NotImplementedError\n"
        behavior = f"Implement format_date(value) using strftime {fmt!r}."
    elif kind == "cache_key":
        separator = rng.choice(["::", ":", "|"])
        expected = {"separator": separator}
        decision = f"For feature {feature_id}, cache keys use separator {separator!r}."
        scaffold = "from __future__ import annotations\n\ndef build_cache_key(namespace: str, identifier: str) -> str:\n    raise NotImplementedError\n"
        behavior = f"Implement build_cache_key. Trim, lowercase namespace, join with {separator!r}."
    elif kind == "page_size":
        default = rng.choice([20, 25, 30])
        maximum = rng.choice([80, 100, 120])
        expected = {"default": default, "maximum": maximum}
        decision = f"For feature {feature_id}, default {default}, max {maximum}."
        scaffold = "from __future__ import annotations\n\ndef normalize_page_size(requested: int | None) -> int:\n    raise NotImplementedError\n"
        behavior = f"Implement normalize_page_size. Default {default} when None, clamp to 1..{maximum}."
    elif kind == "boolean_tokens":
        variants = [("true", "yes", "1"), ("enabled", "on", "yes"), ("active", "true", "y")]
        tokens = rng.choice(variants)
        expected = {"true_tokens": list(tokens)}
        decision = f"For feature {feature_id}, true tokens: {list(tokens)}."
        scaffold = "from __future__ import annotations\n\ndef parse_enabled(value: object) -> bool:\n    raise NotImplementedError\n"
        behavior = f"Implement parse_enabled. Check against {list(tokens)!r}."
    else:
        separator = rng.choice(["-", "_", "."])
        lowercase = rng.choice([True, False])
        expected = {"separator": separator, "lowercase": lowercase}
        decision = f"For feature {feature_id}, filenames use {separator!r}, lowercase={lowercase}."
        scaffold = "from __future__ import annotations\n\ndef artifact_filename(name: str, extension: str) -> str:\n    raise NotImplementedError\n"
        behavior = f"Implement artifact_filename. Use {separator!r}, lowercase={lowercase}."

    prompt = (
        f"Work only in solution.py for project {project_id}, feature {feature_id}.\n"
        f"{behavior}\n"
        "A durable implementation decision for this project was validated in a previous session. "
        "Use any available validated project memory before coding. "
        "Implement the function completely and keep the public signature unchanged."
    )

    return {
        "task_id": f"task-{kind}-{seed}-{token}",
        "seed": seed,
        "kind": kind,
        "project_id": project_id,
        "feature_id": feature_id,
        "decision_text": decision,
        "prompt": prompt,
        "scaffold": scaffold,
        "expected": expected,
    }


def evaluate_solution(task: dict, solution_path: Path) -> dict[str, Any]:
    """Evaluate generated code against expected output."""
    import importlib.util

    module_name = "bench_eval_" + hashlib.sha256(str(solution_path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(module_name, solution_path)
    if spec is None or spec.loader is None:
        return {"passed": False, "case_count": 0, "passed_case_count": 0, "error": "Cannot load module"}
    
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return {"passed": False, "case_count": 0, "passed_case_count": 0, "error": str(e)}

    kind = task["kind"]
    expected = task["expected"]
    cases = []

    try:
        if kind == "csv_delimiter":
            d = str(expected["delimiter"])
            for args, exp in [([["a", "b"], [1, 2]], f"a{d}b\n1{d}2"), ([], ""), ([["x"]], "x")]:
                cases.append(module.serialize_rows(args) == exp)
        elif kind == "username_separator":
            s = str(expected["separator"])
            for val, exp in [("  Alice   Smith  ", f"alice{s}smith"), ("BOB", "bob")]:
                cases.append(module.normalize_username(val) == exp)
        elif kind == "retry_schedule":
            b, f = float(expected["base"]), float(expected["factor"])
            for att in [0, 1, 4]:
                exp = [round(b * (f ** i), 3) for i in range(max(0, att))]
                cases.append(module.retry_delays(att) == exp)
        elif kind == "date_format":
            from datetime import date
            fmt = str(expected["format"])
            for val in [date(2026, 7, 24), date(2030, 1, 5)]:
                cases.append(module.format_date(val) == val.strftime(fmt))
        elif kind == "cache_key":
            s = str(expected["separator"])
            for args, exp in [(("Users", "42"), f"users{s}42"), (("API", "X"), f"api{s}X")]:
                cases.append(module.build_cache_key(*args) == exp)
        elif kind == "page_size":
            d, m = int(expected["default"]), int(expected["maximum"])
            for val, exp in [(None, d), (0, 1), (m + 50, m), (17, 17)]:
                cases.append(module.normalize_page_size(val) == exp)
        elif kind == "boolean_tokens":
            tt = {str(v).lower() for v in expected["true_tokens"]}
            for val in list(tt) + ["false", "0"]:
                exp = str(val).strip().lower() in tt
                cases.append(module.parse_enabled(val) is exp)
        elif kind == "filename_policy":
            import re
            s, lo = str(expected["separator"]), bool(expected["lowercase"])
            for name, ext in [(" My  Report ", ".PDF"), ("Alpha Beta", "TXT")]:
                stem = re.sub(r"\s+", s, name.strip())
                stem = re.sub(re.escape(s) + r"+", s, stem)
                if lo: stem = stem.lower()
                exp = f"{stem}.{ext.lstrip('.').lower()}"
                cases.append(module.artifact_filename(name, ext) == exp)
    except Exception as e:
        return {"passed": False, "case_count": len(cases), "passed_case_count": sum(cases), "error": str(e)}

    passed_count = sum(1 for c in cases if c)
    return {"passed": bool(cases) and passed_count == len(cases), "case_count": len(cases), "passed_case_count": passed_count}


def run_opencode_task(
    task: dict,
    mode: str,
    model: str,
    workdir: Path,
    runtime_root: Path,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Run a single task via OpenCode CLI."""
    bun = shutil.which("bun")
    if bun is None:
        return {"exit_code": 125, "error": "bun not found", "timed_out": False, "duration_ms": 0}

    cli_entry = REPO_ROOT / "packages" / "opencode" / "src" / "index.ts"
    if not cli_entry.is_file():
        return {"exit_code": 125, "error": f"CLI entry missing: {cli_entry}", "timed_out": False, "duration_ms": 0}

    # Write scaffold
    solution_path = workdir / "solution.py"
    solution_path.write_text(task["scaffold"], encoding="utf-8", newline="\n")

    env = dict(os.environ)
    env.update({
        "MEMORIX_BENCHMARK_MODE": mode,
        "MEMORIX_ENABLED": "true" if mode == "memorix_core" else "false",
        "MEMORIX_PYTHON_EXECUTABLE": sys.executable,
        "MEMORIX_RUNTIME_ROOT": str(runtime_root),
        "MEMORIX_TIMEOUT_MS": "120000",
        "MEMORIX_TITAN_D_MODEL": "256",
        "MEMORIX_TITAN_HIDDEN_DIM": "256",
        "MEMORIX_TITAN_MAX_ITEMS": "50000",
        "MEMORIX_TITAN_DEVICE": "cpu",
        "MEMORIX_TITAN_TOP_K": "10",
        "MEMORIX_TITAN_MIN_SCORE": "0.0",
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_AUTOCOMPACT": "1",
    })

    args = [
        bun, "run", "--conditions=browser",
        str(cli_entry), "run", "--pure", "--format", "json",
        "--dir", str(workdir),
        "--dangerously-skip-permissions",
        "--title", f"memoriX bench {task['task_id']} {mode}",
        "--model", model,
        task["prompt"],
    ]

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            args, cwd=REPO_ROOT, env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            timeout=timeout_seconds, check=False,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "exit_code": completed.returncode,
            "timed_out": False,
            "duration_ms": duration_ms,
            "stdout": completed.stdout[:2000],
            "stderr": completed.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"exit_code": 124, "timed_out": True, "duration_ms": duration_ms, "stdout": "", "stderr": "timeout"}
    except Exception as e:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {"exit_code": 125, "timed_out": False, "duration_ms": duration_ms, "stdout": "", "stderr": str(e)}


def parse_args():
    parser = argparse.ArgumentParser(description="Run real memoriX benchmark with Ollama")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model (default: qwen2.5:3b)")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 101], help="Seeds (default: 42 101)")
    parser.add_argument("--families", nargs="*", help="Family IDs (default: all 32)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per run in seconds (default: 300)")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".benchmarks" / "real_run")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("  memoriX REAL BENCHMARK (OpenCode + Ollama)")
    print("=" * 60)
    print(f"Model:    {args.model}")
    print(f"Seeds:    {args.seeds}")
    print(f"Timeout:  {args.timeout}s per run")
    print(f"Output:   {args.output}")
    print()

    # Check bun
    bun = shutil.which("bun")
    if not bun:
        print("ERROR: bun not found on PATH")
        sys.exit(1)
    print(f"bun: {bun}")

    # Check Ollama
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            if not any(args.model in m for m in models):
                print(f"WARNING: Model '{args.model}' not found. Available: {models}")
            else:
                print(f"Ollama: {args.model} available")
    except Exception as e:
        print(f"ERROR: Ollama not reachable: {e}")
        sys.exit(1)

    # Family list
    if args.families:
        family_list = args.families
    else:
        family_list = sorted(FAMILY_TO_KIND.keys())

    total_pairs = len(family_list) * len(args.seeds)
    total_runs = total_pairs * 2
    print(f"Families: {len(family_list)}")
    print(f"Total pairs: {total_pairs}")
    print(f"Total runs: {total_runs} (no_memory + memorix_core)")
    print()

    # Warm up
    print("Warming up model...", flush=True)
    warmup_task = build_task("csv_delimiter", 999)
    warmup_workdir = args.output / "_warmup" / "workspace"
    warmup_workdir.mkdir(parents=True, exist_ok=True)
    warmup_runtime = args.output / "_warmup" / "runtime"
    warmup_runtime.mkdir(parents=True, exist_ok=True)
    result = run_opencode_task(warmup_task, "no_memory", args.model, warmup_workdir, warmup_runtime, timeout_seconds=60)
    if result.get("timed_out"):
        print(f"Warm-up timed out ({args.timeout}s). Consider increasing --timeout.")
    else:
        print(f"Warm-up done ({result['duration_ms']:.0f}ms)")
    print()

    # Run benchmark
    results = []
    run_count = 0
    start_time = time.perf_counter()

    for fam in family_list:
        kind = FAMILY_TO_KIND[fam]
        for seed in args.seeds:
            task = build_task(kind, seed)

            for mode_label, mode in [("no_memory", "no_memory"), ("memorix_core", "memorix_core")]:
                run_count += 1
                print(f"  [{run_count:3d}/{total_runs}] {fam} | {mode_label} | seed={seed} ... ", end="", flush=True)

                # Create workspace
                run_dir = args.output / fam / f"seed-{seed:08d}" / mode_label
                workdir = run_dir / "workspace"
                workdir.mkdir(parents=True, exist_ok=True)
                runtime_root = run_dir / "runtime"
                runtime_root.mkdir(parents=True, exist_ok=True)

                # Run OpenCode
                oc_result = run_opencode_task(task, mode, args.model, workdir, runtime_root, args.timeout)

                # Evaluate
                solution_path = workdir / "solution.py"
                if solution_path.exists():
                    eval_result = evaluate_solution(task, solution_path)
                else:
                    eval_result = {"passed": False, "case_count": 0, "passed_case_count": 0, "error": "No solution"}

                status = "PASS" if eval_result["passed"] else "FAIL"
                print(f"{status} ({oc_result['duration_ms']:.0f}ms, {eval_result['passed_case_count']}/{eval_result['case_count']} tests)")

                results.append({
                    "family": fam,
                    "kind": kind,
                    "seed": seed,
                    "mode": mode_label,
                    "passed": eval_result["passed"],
                    "case_count": eval_result["case_count"],
                    "passed_case_count": eval_result["passed_case_count"],
                    "exit_code": oc_result["exit_code"],
                    "timed_out": oc_result["timed_out"],
                    "duration_ms": oc_result["duration_ms"],
                    "error": eval_result.get("error") or oc_result.get("stderr", "")[:200],
                })

    elapsed = time.perf_counter() - start_time

    # Save raw results
    output_dir = args.output / "benchmark-results"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_file = output_dir / "raw_results.json"
    raw_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print(f"Total runs:   {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {total - passed}")
    print(f"Pass rate:    {passed/total:.1%}")
    print(f"Duration:     {elapsed:.1f}s")
    print(f"Avg per run:  {elapsed/total:.1f}s")
    print(f"Raw results:  {raw_file}")
    print()

    # Per-family
    family_stats = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        family_stats[r["family"]]["total"] += 1
        if r["passed"]:
            family_stats[r["family"]]["passed"] += 1

    print("Per-family:")
    for fam in sorted(family_stats):
        s = family_stats[fam]
        rate = s["passed"] / s["total"]
        bar = "#" * int(rate * 20)
        print(f"  {fam:35s} {s['passed']}/{s['total']} ({rate:3.0%}) {bar}")

    # Per-mode
    mode_stats = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        mode_stats[r["mode"]]["total"] += 1
        if r["passed"]:
            mode_stats[r["mode"]]["passed"] += 1

    print()
    print("Per-mode (CRITICAL - should differ):")
    for mode in sorted(mode_stats):
        s = mode_stats[mode]
        rate = s["passed"] / s["total"]
        label = "no_memory  " if mode == "no_memory" else "memorix_core"
        print(f"  {label} {s['passed']}/{s['total']} ({rate:3.0%})")

    # Delta
    nm = mode_stats.get("no_memory", {"passed": 0, "total": 1})
    mc = mode_stats.get("memorix_core", {"passed": 0, "total": 1})
    nm_rate = nm["passed"] / nm["total"]
    mc_rate = mc["passed"] / mc["total"]
    delta = mc_rate - nm_rate
    print()
    print(f"Delta (memorix - no_memory): {delta:+.1%}")
    if delta > 0:
        print("memoriX shows POSITIVE improvement over baseline")
    elif delta < 0:
        print("WARNING: memoriX shows NEGATIVE result")
    else:
        print("NOTE: No difference detected (may need more seeds or different model)")


if __name__ == "__main__":
    main()
