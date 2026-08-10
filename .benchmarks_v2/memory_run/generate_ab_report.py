#!/usr/bin/env python3
"""Generate A/B comparison report from memory benchmark raw results."""

import json
import csv
import statistics
from pathlib import Path

# --- Paths ---
RAW_PATH = Path(r"C:\GitHub\memoriX\.benchmarks_v2\memory_run\memory-benchmark-results\raw_results.json")
REPORT_PATH = Path(r"C:\GitHub\memoriX\.benchmarks_v2\memory_run\ab-comparison\ab-comparison-report.md")
CSV_PATH = Path(r"C:\GitHub\memoriX\.benchmarks_v2\memory_run\ab-comparison\ab-summary.csv")

# --- Load raw results ---
with open(RAW_PATH, "r", encoding="utf-8") as f:
    raw = json.load(f)

# --- Split by mode ---
no_mem = [r for r in raw if r["mode"] == "no_memory"]
mem    = [r for r in raw if r["mode"] == "memorix_core"]

# --- Build per-family aggregates ---
families = sorted(set(r["family"] for r in raw))

rows = []  # list of dicts for CSV / report
for fam in families:
    nm_runs = [r for r in no_mem if r["family"] == fam]
    mm_runs = [r for r in mem    if r["family"] == fam]

    nm_total = len(nm_runs)
    nm_passed = sum(1 for r in nm_runs if r["passed"])
    nm_rate = (nm_passed / nm_total * 100) if nm_total else 0.0

    mm_total = len(mm_runs)
    mm_passed = sum(1 for r in mm_runs if r["passed"])
    mm_rate = (mm_passed / mm_total * 100) if mm_total else 0.0

    delta = mm_rate - nm_rate

    nm_latencies = [r["llm_ms"] for r in nm_runs if r["llm_ms"] is not None]
    mm_latencies = [r["llm_ms"] for r in mm_runs if r["llm_ms"] is not None]

    nm_median_lat = statistics.median(nm_latencies) if nm_latencies else 0.0
    mm_median_lat = statistics.median(mm_latencies) if mm_latencies else 0.0

    rows.append({
        "family": fam,
        "no_memory_passed": nm_passed,
        "no_memory_total": nm_total,
        "no_memory_rate": nm_rate,
        "memorix_core_passed": mm_passed,
        "memorix_core_total": mm_total,
        "memorix_core_rate": mm_rate,
        "delta_pp": delta,
        "median_lat_no_memory_ms": nm_median_lat,
        "median_lat_memorix_core_ms": mm_median_lat,
    })

# --- Overall statistics ---
overall_nm_total  = sum(r["no_memory_total"] for r in rows)
overall_nm_passed = sum(r["no_memory_passed"] for r in rows)
overall_mm_total  = sum(r["memorix_core_total"] for r in rows)
overall_mm_passed = sum(r["memorix_core_passed"] for r in rows)

overall_nm_rate = (overall_nm_passed / overall_nm_total * 100) if overall_nm_total else 0.0
overall_mm_rate = (overall_mm_passed / overall_mm_total * 100) if overall_mm_total else 0.0
overall_delta   = overall_mm_rate - overall_nm_rate

# Families won / lost / tied
fam_won   = sum(1 for r in rows if r["delta_pp"] > 0.0)
fam_lost  = sum(1 for r in rows if r["delta_pp"] < 0.0)
fam_tied  = sum(1 for r in rows if r["delta_pp"] == 0.0)

# Latency aggregates (median of per-family medians)
all_nm_lat = [r["median_lat_no_memory_ms"] for r in rows if r["median_lat_no_memory_ms"] > 0]
all_mm_lat = [r["median_lat_memorix_core_ms"] for r in rows if r["median_lat_memorix_core_ms"] > 0]
median_nm_lat = statistics.median(all_nm_lat) if all_nm_lat else 0.0
median_mm_lat = statistics.median(all_mm_lat) if all_mm_lat else 0.0

# Key findings buckets
strong   = [r for r in rows if r["delta_pp"] >= 25.0]
moderate = [r for r in rows if 5.0 <= r["delta_pp"] < 25.0]
no_imp   = [r for r in rows if r["delta_pp"] < 5.0]  # includes regressions

# --- Write CSV ---
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "family",
        "no_memory_passed", "no_memory_total", "no_memory_rate",
        "memorix_core_passed", "memorix_core_total", "memorix_core_rate",
        "delta_pp",
        "median_lat_no_memory_ms", "median_lat_memorix_core_ms",
    ])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# --- Build Markdown report ---
def _rate_bar(rate: float) -> str:
    """Return a simple text bar for the rate."""
    filled = round(rate / 10)
    return "#" * filled + "." * (10 - filled)

md = []
md.append("# A/B Comparison Report: memoriX Core vs No-Memory Baseline")
md.append("")
md.append("---")
md.append("")

# Executive Summary
md.append("## Executive Summary")
md.append("")
md.append("| Metric | No-Memory | With-Memory (memorix_core) | Delta |")
md.append("|--------|-----------|---------------------------|-------|")
md.append(f"| Overall pass rate | {overall_nm_rate:.1f}% ({overall_nm_passed}/{overall_nm_total}) "
          f"| {overall_mm_rate:.1f}% ({overall_mm_passed}/{overall_mm_total}) "
          f"| **{overall_delta:+.1f}pp** |")
md.append(f"| Median family latency | {median_nm_lat:.0f} ms "
          f"| {median_mm_lat:.0f} ms "
          f"| {median_mm_lat - median_nm_lat:+.0f} ms |")
md.append(f"| Families evaluated | {len(families)} | {len(families)} | — |")
md.append(f"| Families won (delta > 0) | — | {fam_won} | — |")
md.append(f"| Families lost (delta < 0) | — | {fam_lost} | — |")
md.append(f"| Families tied (delta = 0) | — | {fam_tied} | — |")
md.append("")

# Per-Family A/B Comparison
md.append("## Per-Family A/B Comparison")
md.append("")
md.append("| Family | No-Memory Rate | With-Memory Rate | Delta (pp) | Median Lat No-Mem (ms) | Median Lat With-Mem (ms) |")
md.append("|--------|---------------|------------------|------------|------------------------|--------------------------|")
for r in sorted(rows, key=lambda x: x["delta_pp"], reverse=True):
    md.append(
        f"| `{r['family']}` "
        f"| {r['no_memory_rate']:.1f}% ({r['no_memory_passed']}/{r['no_memory_total']}) "
        f"| {r['memorix_core_rate']:.1f}% ({r['memorix_core_passed']}/{r['memorix_core_total']}) "
        f"| **{r['delta_pp']:+.1f}** "
        f"| {r['median_lat_no_memory_ms']:.0f} "
        f"| {r['median_lat_memorix_core_ms']:.0f} |"
    )
md.append("")

# Key Findings
md.append("## Key Findings")
md.append("")

md.append("### Strong Improvement (>= +25pp)")
md.append("")
if strong:
    for r in sorted(strong, key=lambda x: x["delta_pp"], reverse=True):
        md.append(f"- **`{r['family']}`**: {r['delta_pp']:+.1f}pp "
                  f"({r['no_memory_rate']:.0f}% -> {r['memorix_core_rate']:.0f}%)")
else:
    md.append("- No families with >= +25pp improvement.")
md.append("")

md.append("### Moderate Improvement (+5pp to +25pp)")
md.append("")
if moderate:
    for r in sorted(moderate, key=lambda x: x["delta_pp"], reverse=True):
        md.append(f"- **`{r['family']}`**: {r['delta_pp']:+.1f}pp "
                  f"({r['no_memory_rate']:.0f}% -> {r['memorix_core_rate']:.0f}%)")
else:
    md.append("- No families with moderate improvement.")
md.append("")

md.append("### No Significant Improvement / Regression (< +5pp)")
md.append("")
if no_imp:
    for r in sorted(no_imp, key=lambda x: x["delta_pp"]):
        label = "REGRESSION" if r["delta_pp"] < 0 else "no change"
        md.append(f"- **`{r['family']}`**: {r['delta_pp']:+.1f}pp ({label}) "
                  f"({r['no_memory_rate']:.0f}% -> {r['memorix_core_rate']:.0f}%)")
else:
    md.append("- None.")
md.append("")

# Methodology
md.append("## Methodology")
md.append("")
md.append("- **Approach**: Prompt injection -- the LLM receives the full task prompt along with retrieved memory context (memorix_core) or without (no_memory).")
md.append("- **Model**: `qwen2.5:3b` served locally via Ollama.")
md.append(f"- **Design**: {len(set(r['seed'] for r in raw))} seeds x {len(families)} families x 2 modes = {len(raw)} total runs.")
md.append("- **Pass criteria**: All test cases for a given seed/family must pass for the run to be marked passed.")
md.append("- **Latency**: Wall-clock LLM inference time per run (llm_ms).")
md.append("")

# Raw Data
md.append("## Raw Data")
md.append("")
md.append(f"Source file: `{RAW_PATH}`")
md.append(f"CSV summary: `{CSV_PATH}`")
md.append("")
md.append("---")
md.append("*Report generated by `generate_ab_report.py`*")
md.append("")

# --- Write report ---
with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))

# --- Print summary to stdout ---
print("=" * 72)
print("  A/B COMPARISON SUMMARY")
print("=" * 72)
print(f"  No-Memory    : {overall_nm_rate:6.1f}% pass ({overall_nm_passed}/{overall_nm_total})")
print(f"  With-Memory  : {overall_mm_rate:6.1f}% pass ({overall_mm_passed}/{overall_mm_total})")
print(f"  Delta        : {overall_delta:+6.1f}pp")
print(f"  Families won : {fam_won}  lost: {fam_lost}  tied: {fam_tied}")
print(f"  Median lat. (no-mem)   : {median_nm_lat:.0f} ms")
print(f"  Median lat. (memorix)  : {median_mm_lat:.0f} ms")
print("-" * 72)
print(f"  Report : {REPORT_PATH}")
print(f"  CSV    : {CSV_PATH}")
print("=" * 72)
