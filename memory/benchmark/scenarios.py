"""Deterministic synthetic scenarios for memory-design benchmarks."""

from __future__ import annotations

from memory.benchmark.contracts import (
    BenchmarkScenario,
)


def build_benchmark_scenarios() -> tuple[
    BenchmarkScenario,
    ...,
]:
    """Return fixed scenarios covering stable, spike and sustained pressure."""

    scenarios = (
        BenchmarkScenario(
            scenario_id="stable",
            scope_id="block_stable",
            capacity=100,
            used_items=30,
            usage_samples=(20, 25, 30),
            term_frequencies={
                "stable": 8,
            },
            surprise_samples=(0.1, 0.2),
            previous_pressure_samples=(
                0.20,
                0.25,
                0.30,
            ),
            documents=(
                "Stable retrieval architecture.",
                "Stable retrieval contract.",
                "Stable validated memory.",
            ),
            expected_pressure="stable",
            expected_expand=False,
            expected_pruning_actions=False,
        ),
        BenchmarkScenario(
            scenario_id="single_spike",
            scope_id="block_single_spike",
            capacity=100,
            used_items=95,
            usage_samples=(20, 20, 95),
            term_frequencies={
                "single": 10,
            },
            surprise_samples=(0.2,),
            previous_pressure_samples=(
                0.20,
                0.30,
                0.25,
            ),
            documents=(
                "Temporary traffic spike.",
                "Temporary capacity event.",
                "No sustained pressure.",
            ),
            expected_pressure="watch",
            expected_expand=False,
            expected_pruning_actions=False,
        ),
        BenchmarkScenario(
            scenario_id="persistent_pressure",
            scope_id="block_persistent",
            capacity=100,
            used_items=95,
            usage_samples=(60, 75, 85, 95),
            term_frequencies={
                "alpha": 1,
                "beta": 1,
                "gamma": 1,
                "delta": 1,
            },
            surprise_samples=(0.8, 0.9),
            previous_pressure_samples=(
                0.80,
                0.82,
                0.85,
            ),
            documents=(
                "Astronomy telescope stars.",
                "Astronomy planets research.",
                "Astronomy orbital observations.",
                "Guitar concert melody.",
            ),
            expected_pressure="high",
            expected_expand=True,
            expected_pruning_actions=True,
        ),
    )

    for scenario in scenarios:
        scenario.validate()

    return scenarios
