from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
from memory.adaptive import inspect_runtime_policy_search

@dataclass(frozen=True, slots=True)
class PolicySearchBenchmarkReport:
    results: tuple[dict[str, Any], ...]
    repetitions: int
    synthetic_data_only: bool = True
    dry_run: bool = True
    policy_applied: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    def to_dict(self) -> dict[str, Any]: return asdict(self)

def run_policy_search_benchmark(*, runtime_root: str | Path, repetitions: int = 3) -> PolicySearchBenchmarkReport:
    if repetitions < 1: raise ValueError("repetitions must be positive.")
    rows = []
    for count in (10_000, 100_000, 1_000_000, 6_000_000):
        timings = []
        best = None
        for _ in range(repetitions):
            started = perf_counter()
            report = inspect_runtime_policy_search(runtime_root=runtime_root, max_trials=12, assessment_limit=10, simulated_memory_count=count)
            timings.append(perf_counter() - started)
            best = report.search_result.best_policy.policy_id
        rows.append({"simulated_memory_count": count, "best_policy_id": best, "mean_seconds": sum(timings) / len(timings), "max_seconds": max(timings)})
    return PolicySearchBenchmarkReport(results=tuple(rows), repetitions=repetitions)
