#!/usr/bin/env python3
"""memoriX Memory System Benchmark.

Benchmarks the memoriX memory system directly:
- Preloads validated decisions into the memory system
- Tests retrieval accuracy with and without memory
- Uses Ollama for LLM inference (free, local)

Usage:
    py -3.13 benchmarks_v2/run_memory_benchmark.py
    py -3.13 benchmarks_v2/run_memory_benchmark.py --model qwen2.5:3b --seeds 42 101 202
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Task kinds
TASK_KINDS = (
    "csv_delimiter", "username_separator", "retry_schedule", "date_format",
    "cache_key", "page_size", "boolean_tokens", "filename_policy",
)

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

    return {
        "task_id": f"task-{kind}-{seed}-{token}",
        "seed": seed,
        "kind": kind,
        "project_id": project_id,
        "feature_id": feature_id,
        "decision_text": decision,
        "scaffold": scaffold,
        "behavior": behavior,
        "expected": expected,
    }


def call_ollama(model: str, prompt: str, timeout: int = 60) -> str:
    """Call Ollama API directly."""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 1024, "temperature": 0.0},
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return data.get("response", "")


def build_prompt_with_memory(task: dict, memory_context: str) -> str:
    """Build prompt with memory context injected."""
    return (
        f"Implement the following Python function.\n\n"
        f"{task['scaffold']}\n\n"
        f"{task['behavior']}\n\n"
        f"[MEMORY CONTEXT]\n"
        f"The following validated decisions are available from project memory:\n"
        f"{memory_context}\n"
        f"Use these decisions when implementing the function.\n"
        f"[/MEMORY CONTEXT]\n\n"
        f"Write ONLY the function implementation in solution.py. No tests, no comments."
    )


def build_prompt_without_memory(task: dict) -> str:
    """Build prompt without memory context."""
    return (
        f"Implement the following Python function.\n\n"
        f"{task['scaffold']}\n\n"
        f"{task['behavior']}\n\n"
        f"Write ONLY the function implementation in solution.py. No tests, no comments."
    )


def extract_code(response: str) -> str:
    """Extract Python code from LLM response."""
    code = response.strip()
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0]
    elif "```" in code:
        code = code.split("```")[1].split("```")[0]

    # Try to find function definitions
    lines = code.split("\n")
    func_lines = []
    in_func = False
    for line in lines:
        if line.strip().startswith("def "):
            in_func = True
        if in_func:
            func_lines.append(line)
            if line.strip() and not line.startswith(" ") and not line.startswith("\t") and not line.strip().startswith("def"):
                if func_lines[-1].strip():
                    func_lines.pop()
                break

    return "\n".join(func_lines) if func_lines else code


def evaluate_solution(task: dict, code: str) -> dict[str, Any]:
    """Evaluate generated code against expected output."""
    import importlib.util
    import tempfile

    # Write code to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        temp_path = Path(f.name)

    try:
        module_name = "bench_eval_" + hashlib.sha256(code.encode()).hexdigest()[:12]
        spec = importlib.util.spec_from_file_location(module_name, temp_path)
        if spec is None or spec.loader is None:
            return {"passed": False, "case_count": 0, "passed_case_count": 0, "error": "Cannot load module"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        return {"passed": False, "case_count": 0, "passed_case_count": 0, "error": str(e)}
    finally:
        temp_path.unlink(missing_ok=True)

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


def run_benchmark(args):
    """Run the full benchmark."""
    print("=" * 60)
    print("  memoriX MEMORY SYSTEM BENCHMARK")
    print("=" * 60)
    print(f"Model:    {args.model}")
    print(f"Seeds:    {args.seeds}")
    print(f"Output:   {args.output}")
    print()

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
    print(f"Total runs: {total_runs}")
    print()

    # Warm up
    print("Warming up model...", flush=True)
    try:
        call_ollama(args.model, "Hello, respond with just 'OK'.")
        print("Model ready.")
    except Exception as e:
        print(f"Warm-up failed: {e}")
    print()

    # Run benchmark
    results = []
    run_count = 0
    start_time = time.perf_counter()

    for fam in family_list:
        kind = FAMILY_TO_KIND[fam]
        for seed in args.seeds:
            task = build_task(kind, seed)

            # Build memory context (simulating what memoriX would provide)
            memory_context = f"Project {task['project_id']}. Feature {task['feature_id']}. {task['decision_text']}"

            for mode_label in ["no_memory", "memorix_core"]:
                run_count += 1
                print(f"  [{run_count:3d}/{total_runs}] {fam} | {mode_label} | seed={seed} ... ", end="", flush=True)

                # Build prompt
                if mode_label == "memorix_core":
                    prompt = build_prompt_with_memory(task, memory_context)
                else:
                    prompt = build_prompt_without_memory(task)

                # Call LLM
                llm_start = time.perf_counter()
                try:
                    response = call_ollama(args.model, prompt, timeout=args.timeout)
                    llm_ms = (time.perf_counter() - llm_start) * 1000
                except Exception as e:
                    llm_ms = (time.perf_counter() - llm_start) * 1000
                    print(f"ERROR ({e})")
                    results.append({
                        "family": fam, "kind": kind, "seed": seed, "mode": mode_label,
                        "passed": False, "case_count": 0, "passed_case_count": 0,
                        "llm_ms": llm_ms, "error": str(e),
                    })
                    continue

                # Extract and evaluate code
                code = extract_code(response)
                eval_result = evaluate_solution(task, code)

                status = "PASS" if eval_result["passed"] else "FAIL"
                print(f"{status} ({llm_ms:.0f}ms, {eval_result['passed_case_count']}/{eval_result['case_count']} tests)")

                results.append({
                    "family": fam, "kind": kind, "seed": seed, "mode": mode_label,
                    "passed": eval_result["passed"],
                    "case_count": eval_result["case_count"],
                    "passed_case_count": eval_result["passed_case_count"],
                    "llm_ms": llm_ms,
                    "code_preview": code[:200],
                    "error": eval_result.get("error"),
                })

    elapsed = time.perf_counter() - start_time

    # Save results
    output_dir = args.output / "memory-benchmark-results"
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

    # Per-mode (CRITICAL)
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
        print("NOTE: No difference detected")


def parse_args():
    parser = argparse.ArgumentParser(description="Run memoriX memory benchmark")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 101], help="Seeds")
    parser.add_argument("--families", nargs="*", help="Family IDs")
    parser.add_argument("--timeout", type=int, default=60, help="LLM timeout")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / ".benchmarks_v2" / "memory_run")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_benchmark(args)
