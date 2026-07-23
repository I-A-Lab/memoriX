"""Bounded synthetic benchmark for adaptive retention ranking."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from memory.adaptive import inspect_runtime_retention_ranking

DEFAULT_RETENTION_SCENARIOS = (10_000, 100_000, 1_000_000, 6_000_000)


@dataclass(frozen=True, slots=True)
class RetentionRankingBenchmarkResult:
    simulated_memory_count: int
    elapsed_ms: float
    mean_retention: float
    minimum_retention: float
    assessment_count: int
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_retention_ranking_benchmark(
    *,
    runtime_root: str | Path,
    scenarios: Iterable[int] = DEFAULT_RETENTION_SCENARIOS,
    repetitions: int = 3,
    assessment_limit: int = 1,
) -> dict[str, Any]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive.")

    results: list[dict[str, Any]] = []
    for count in scenarios:
        if count < 0:
            raise ValueError("scenarios must be non-negative.")

        durations: list[float] = []
        report = None
        for _ in range(repetitions):
            started = perf_counter()
            report = inspect_runtime_retention_ranking(
                runtime_root=runtime_root,
                simulated_memory_count=count,
                assessment_limit=assessment_limit,
            )
            durations.append((perf_counter() - started) * 1000.0)

        assert report is not None
        results.append(
            RetentionRankingBenchmarkResult(
                simulated_memory_count=count,
                elapsed_ms=sum(durations) / len(durations),
                mean_retention=report.ranking.mean_retention,
                minimum_retention=report.ranking.minimum_retention,
                assessment_count=len(report.ranking.assessments),
            ).to_dict()
        )

    return {
        "status": "ok",
        "synthetic_data_only": True,
        "dry_run": True,
        "actions_applied": False,
        "runtime_modified": False,
        "cold_site_accessed": False,
        "neural_model_loaded": False,
        "repetitions": repetitions,
        "assessment_limit": assessment_limit,
        "results": results,
    }
