"""Smoke test with Ollama backend."""
import sys
sys.path.insert(0, r"C:\GitHub\memoriX")

from pathlib import Path
from collections import defaultdict
from benchmarks_v2.orchestrator.llm_backends import OllamaBackend
from benchmarks_v2.orchestrator.orchestrator import BenchmarkOrchestrator
from benchmarks_v2.orchestrator.data_models import CampaignManifest

# Create backend
backend = OllamaBackend(model="qwen2.5:3b")

# Create orchestrator with backend
output_dir = Path(r"C:\GitHub\memoriX\.benchmarks_v2\smoke_ollama_extended")
orchestrator = BenchmarkOrchestrator(output_dir=output_dir, dry_run=False, backend=backend)

# Create manifest
manifest = CampaignManifest(
    campaign_id="smoke-ollama-extended",
    profile_name="smoke",
    seeds=[42, 101],
    total_pairs=2,
    created_by="smoke_test",
)

# Run with 4 families
families = [
    "f01_exact_key_recall",
    "f02_semantic_retrieval",
    "f03_distractor_robustness",
    "f04_multi_hop_reasoning",
]

total_expected = len(families) * 2 * 2
print(f"Running extended smoke pilot with Ollama (qwen2.5:3b)")
print(f"Families: {families}")
print(f"Seeds: [42, 101]")
print(f"Total expected runs: {total_expected}")
print("=" * 60)

results = orchestrator.run(manifest, families=families)

# Summary
print()
print("RESULTS SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r.status == "passed")
total = len(results)
print(f"Total runs: {total}")
print(f"Passed: {passed}")
print(f"Failed: {total - passed}")
print(f"Pass rate: {passed/total:.1%}")
print()

# Per-family breakdown
family_stats = defaultdict(lambda: {"passed": 0, "total": 0})
for r in results:
    family_stats[r.family]["total"] += 1
    if r.status == "passed":
        family_stats[r.family]["passed"] += 1

print("Per-family breakdown:")
for fam, stats in sorted(family_stats.items()):
    rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
    print(f"  {fam}: {stats['passed']}/{stats['total']} ({rate:.0%})")

# Per-mode breakdown
mode_stats = defaultdict(lambda: {"passed": 0, "total": 0})
for r in results:
    mode_stats[r.mode]["total"] += 1
    if r.status == "passed":
        mode_stats[r.mode]["passed"] += 1

print()
print("Per-mode breakdown:")
for mode, stats in sorted(mode_stats.items()):
    rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
    label = "no_memory" if mode == "A" else "memorix_core"
    print(f"  {label}: {stats['passed']}/{stats['total']} ({rate:.0%})")
