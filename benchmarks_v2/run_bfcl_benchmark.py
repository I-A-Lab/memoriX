#!/usr/bin/env python3
"""BFCL-derived benchmark runner (Canary, Pilots, Blind Curation, Robustness)."""
from __future__ import annotations
import argparse
import json
import random
import sys
import time
import urllib.request
from pathlib import Path
from bfcl_harness import (
    BFCLQuestion, call_ollama, generate_bfcl_dataset, run_oracle_pilot,
    run_blind_curation, run_robustness, save_bfcl_results,
)


def parse_args():
    """Parse command-line arguments for the BFCL-derived benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Run the BFCL-derived benchmark harness "
        "(canary, pilots, blind curation, robustness)."
    )
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model name")
    parser.add_argument(
        "--timeout", type=int, default=60, help="Per LLM call timeout in seconds"
    )
    parser.add_argument(
        "--scale", type=int, default=5, help="Question-count multiplier (x5)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"C:\GitHub\memoriX\.benchmarks_v2\bfcl_run"),
        help="Directory for campaign reports and the summary file",
    )
    parser.add_argument("--skip-canary", action="store_true", help="Skip the canary campaign")
    parser.add_argument("--skip-pilot5", action="store_true", help="Skip the pilot5 campaign")
    parser.add_argument("--skip-pilot25", action="store_true", help="Skip the pilot25 campaign")
    parser.add_argument("--skip-blind", action="store_true", help="Skip the blind curation campaign")
    parser.add_argument(
        "--skip-robustness", action="store_true", help="Skip the robustness campaign"
    )
    return parser.parse_args()


def warmup(model: str, timeout: int) -> None:
    """Send a trivial prompt to confirm the model responds."""
    try:
        response = call_ollama(model, "Hello, respond with just OK.", timeout=timeout)
        if response.startswith("[ollama_error"):
            raise RuntimeError(response)
        print("Model ready.")
    except Exception as exc:
        print(f"WARNING: warm-up failed: {exc}")


def run_oracle_questions(questions: list[BFCLQuestion], model: str, timeout: int,
                         label: str, total_estimate: int, counter: int) -> tuple[dict, int]:
    """Run the oracle pilot campaign one question at a time with progress output.

    Each question costs two LLM calls (baseline without memory, memorix with
    memory), so the global run counter advances by two per question.
    """
    results = []
    baseline_correct = 0
    memorix_correct = 0
    for question in questions:
        start = time.perf_counter()
        data = run_oracle_pilot([question], model, timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result = data["results"][0]
        summary = data["summary"]
        results.append(result)
        baseline_correct += summary["baseline_correct"]
        memorix_correct += summary["memorix_correct"]
        counter += 2
        baseline_status = "OK" if result["baseline_correct"] else "FAIL"
        memorix_status = "OK" if result["memorix_correct"] else "FAIL"
        print(
            f"  [{counter:3d}/{total_estimate}] {label} | "
            f"qid={result['question_id']} baseline={baseline_status} "
            f"memorix={memorix_status} ({elapsed_ms:.0f}ms)"
        )
    total = len(questions)
    return (
        {
            "campaign": "oracle_pilot",
            "results": results,
            "summary": {
                "total_pairs": total,
                "baseline_correct": baseline_correct,
                "memorix_correct": memorix_correct,
                "rate_memorix": memorix_correct / total if total else 0.0,
            },
        },
        counter,
    )


def run_blind_questions(questions: list[BFCLQuestion], model: str, timeout: int,
                        label: str, total_estimate: int, counter: int) -> tuple[dict, int]:
    """Run the blind curation campaign one question at a time with progress output.

    Each question costs one LLM call (the memory-augmented prompt), so the
    global run counter advances by one per question.
    """
    results = []
    corpus_ok = 0
    retrieval_ok = 0
    correct = 0
    for question in questions:
        start = time.perf_counter()
        data = run_blind_curation([question], model, timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        result = data["results"][0]
        summary = data["summary"]
        results.append(result)
        corpus_ok += summary["corpus_contains_reference"]
        retrieval_ok += summary["retrieval_contains_reference"]
        correct += summary["correct_answer"]
        counter += 1
        retrieval_status = "OK" if result["retrieval_contains_reference"] else "FAIL"
        answer_status = "OK" if result["correct_answer"] else "FAIL"
        print(
            f"  [{counter:3d}/{total_estimate}] {label} | "
            f"qid={result['question_id']} retrieval={retrieval_status} "
            f"answer={answer_status} ({elapsed_ms:.0f}ms)"
        )
    total = len(questions)
    return (
        {
            "campaign": "blind_curation",
            "results": results,
            "summary": {
                "total_questions": total,
                "corpus_contains_reference": corpus_ok,
                "retrieval_contains_reference": retrieval_ok,
                "correct_answer": correct,
                "rate_corpus_contains_reference": corpus_ok / total if total else 0.0,
                "rate_retrieval_contains_reference": retrieval_ok / total if total else 0.0,
                "rate_correct_answer": correct / total if total else 0.0,
            },
        },
        counter,
    )


def run_robustness_questions(questions: list[BFCLQuestion], model: str, timeout: int,
                             seeds: tuple, label: str, total_estimate: int,
                             counter: int) -> tuple[dict, int]:
    """Run the robustness campaign one question at a time with progress output.

    Each question is re-run once per seed (three LLM calls by default), so the
    global run counter advances by len(seeds) per question.
    """
    results = []
    corpus_ok = 0
    retrieval_ok = 0
    correct = 0
    successful_all = 0
    successful_two = 0
    seed_count = len(seeds)
    for question in questions:
        start = time.perf_counter()
        data = run_robustness([question], model, timeout, seeds=seeds)
        elapsed_ms = (time.perf_counter() - start) * 1000
        summary = data["summary"]
        results.extend(data["results"])
        corpus_ok += summary["corpus_contains_reference"]
        retrieval_ok += summary["retrieval_contains_reference"]
        correct += summary["correct_answer"]
        successful_all += summary["cases_successful_3of3"]
        successful_two += summary["cases_successful_at_least_2of3"]
        counter += seed_count
        seeds_ok = sum(1 for item in data["results"] if item["correct_answer"])
        print(
            f"  [{counter:3d}/{total_estimate}] {label} | "
            f"qid={question.question_id} seeds={seeds_ok}/{seed_count} "
            f"({elapsed_ms:.0f}ms)"
        )
    total = len(questions)
    return (
        {
            "campaign": "robustness",
            "results": results,
            "summary": {
                "total_cases": total,
                "total_runs": len(results),
                "corpus_contains_reference": corpus_ok,
                "retrieval_contains_reference": retrieval_ok,
                "correct_answer": correct,
                "cases_successful_3of3": successful_all,
                "cases_successful_at_least_2of3": successful_two,
            },
        },
        counter,
    )


def main():
    args = parse_args()
    scale = args.scale
    output = args.output

    print("=" * 60)
    print(f"  memoriX BFCL-DERIVED BENCHMARK (x{scale})")
    print("=" * 60)
    print(f"Model:    {args.model}")
    print(f"Scale:    x{scale}")
    print(f"Output:   {output}")
    print()

    # Ollama reachability check (5s timeout, hard failure when unreachable).
    try:
        with urllib.request.urlopen(
            urllib.request.Request("http://localhost:11434/api/tags", method="GET"),
            timeout=5,
        ) as response:
            models_data = json.loads(response.read().decode("utf-8"))
        available = [m.get("name", "") for m in models_data.get("models", [])]
        if not any(args.model in name for name in available):
            print(f"WARNING: model '{args.model}' not found in Ollama. Available: {available}")
        else:
            print(f"Ollama:   reachable, model '{args.model}' available")
    except Exception as exc:
        print(f"ERROR: Ollama not reachable at http://localhost:11434/api/tags: {exc}")
        sys.exit(1)
    print()

    canary_count = 1 * scale
    pilot5_count = 5 * scale
    pilot25_count = 25 * scale
    blind_count = 25 * scale
    robustness_count = 10 * scale

    # Run estimate: oracle pilot pair = 2 LLM calls, blind = 1 call per
    # question (memory prompt), robustness = 3 runs per case.
    canary_runs = 0 if args.skip_canary else canary_count * 2
    pilot5_runs = 0 if args.skip_pilot5 else pilot5_count * 2
    pilot25_runs = 0 if args.skip_pilot25 else pilot25_count * 2
    blind_runs = 0 if args.skip_blind else blind_count * 1
    robustness_runs = 0 if args.skip_robustness else robustness_count * 3
    total_runs_estimate = canary_runs + pilot5_runs + pilot25_runs + blind_runs + robustness_runs

    print(f"Total estimated runs: {total_runs_estimate}")
    print(
        f"  canary {canary_count} ({canary_runs}), pilot5 {pilot5_count} ({pilot5_runs}), "
        f"pilot25 {pilot25_count} ({pilot25_runs}), blind {blind_count} ({blind_runs}), "
        f"robustness {robustness_count} ({robustness_runs})"
    )
    print()

    warmup(args.model, args.timeout)
    print()

    # Generate the full dataset once and slice per campaign.
    questions = generate_bfcl_dataset(count=155, rng=random.Random(42))

    campaigns_data = {}
    run_counter = 0

    if args.skip_canary:
        print("Skipping canary campaign.")
        print()
    else:
        canary_data, run_counter = run_oracle_questions(
            questions[0:canary_count], args.model, args.timeout,
            "canary", total_runs_estimate, run_counter,
        )
        save_bfcl_results(output / "canary", "canary", canary_data)
        campaigns_data["canary"] = canary_data
        print()

    if args.skip_pilot5:
        print("Skipping pilot5 campaign.")
        print()
    else:
        pilot5_data, run_counter = run_oracle_questions(
            questions[0:pilot5_count], args.model, args.timeout,
            "pilot5", total_runs_estimate, run_counter,
        )
        save_bfcl_results(output / "pilot5", "pilot5", pilot5_data)
        campaigns_data["pilot5"] = pilot5_data
        print()

    if args.skip_pilot25:
        print("Skipping pilot25 campaign.")
        print()
    else:
        pilot25_data, run_counter = run_oracle_questions(
            questions[0:pilot25_count], args.model, args.timeout,
            "pilot25", total_runs_estimate, run_counter,
        )
        save_bfcl_results(output / "pilot25", "pilot25", pilot25_data)
        campaigns_data["pilot25"] = pilot25_data
        print()

    if args.skip_blind:
        print("Skipping blind curation campaign.")
        print()
    else:
        blind_data, run_counter = run_blind_questions(
            questions[0:blind_count], args.model, args.timeout,
            "blind", total_runs_estimate, run_counter,
        )
        save_bfcl_results(output / "blind", "blind", blind_data)
        campaigns_data["blind"] = blind_data
        print()

    if args.skip_robustness:
        print("Skipping robustness campaign.")
        print()
    else:
        robustness_data, run_counter = run_robustness_questions(
            questions[0:robustness_count], args.model, args.timeout,
            seeds=(1, 2, 3), label="robustness",
            total_estimate=total_runs_estimate, counter=run_counter,
        )
        save_bfcl_results(output / "robustness", "robustness", robustness_data)
        campaigns_data["robustness"] = robustness_data
        print()

    # Write the cross-campaign summary.
    output.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "scale": scale,
        "model": args.model,
        "campaigns": {
            name: data["summary"] for name, data in campaigns_data.items()
        },
    }
    summary_path = output / "bfcl_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("=" * 60)
    print(f"BFCL BENCHMARK COMPLETE (scale x{scale})")
    if args.skip_canary:
        print("Canary:      skipped")
    else:
        s = canary_data["summary"]
        print(
            f"Canary:      baseline {s['baseline_correct']}/{s['total_pairs']} "
            f"memoriX {s['memorix_correct']}/{s['total_pairs']} ({s['rate_memorix']:.1%})"
        )
    if args.skip_pilot5:
        print("Pilot 5:     skipped")
    else:
        s = pilot5_data["summary"]
        print(
            f"Pilot 5:     baseline {s['baseline_correct']}/{s['total_pairs']} "
            f"memoriX {s['memorix_correct']}/{s['total_pairs']} ({s['rate_memorix']:.1%})"
        )
    if args.skip_pilot25:
        print("Pilot 25:    skipped")
    else:
        s = pilot25_data["summary"]
        print(
            f"Pilot 25:    baseline {s['baseline_correct']}/{s['total_pairs']} "
            f"memoriX {s['memorix_correct']}/{s['total_pairs']} ({s['rate_memorix']:.1%})"
        )
    if args.skip_blind:
        print("Blind:       skipped")
    else:
        s = blind_data["summary"]
        print(
            f"Blind:       corpus {s['corpus_contains_reference']}/{s['total_questions']} "
            f"retrieval {s['retrieval_contains_reference']}/{s['total_questions']} "
            f"answers {s['correct_answer']}/{s['total_questions']}"
        )
    if args.skip_robustness:
        print("Robustness:  skipped")
    else:
        s = robustness_data["summary"]
        print(
            f"Robustness:  corpus {s['corpus_contains_reference']}/{s['total_runs']} "
            f"retrieval {s['retrieval_contains_reference']}/{s['total_runs']} "
            f"answers {s['correct_answer']}/{s['total_runs']} "
            f"(3/3: {s['cases_successful_3of3']}, >=2/3: {s['cases_successful_at_least_2of3']})"
        )
    print(f"Summary:     {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
