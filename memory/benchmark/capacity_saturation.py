"""Synthetic, bounded capacity-saturation benchmark for memoriX."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
import tracemalloc

from memory.adaptive.runtime_capacity import (
    inspect_runtime_capacity,
    validate_external_runtime_root,
)


DEFAULT_SCENARIOS = (10_000, 100_000, 1_000_000, 6_000_000)
PLAN_SAMPLE_LIMIT = 256


@dataclass(frozen=True, slots=True)
class CapacitySaturationResult:
    active_items: int
    configured_capacity: int
    usage_ratio: float
    pressure_level: str
    admission_allowed: bool
    available_slots: int
    required_free_slots: int
    bounded_plan_sample_size: int
    status_latency_ms: float
    decision_latency_ms: float
    plan_latency_ms: float
    peak_traced_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CapacitySaturationReport:
    benchmark_id: str
    configured_capacity: int
    repetitions: int
    results: tuple[CapacitySaturationResult, ...]
    synthetic_data_only: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    actions_applied: bool = False
    maximum_materialized_plan_items: int = PLAN_SAMPLE_LIMIT
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "configured_capacity": self.configured_capacity,
            "repetitions": self.repetitions,
            "results": [item.to_dict() for item in self.results],
            "synthetic_data_only": self.synthetic_data_only,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "actions_applied": self.actions_applied,
            "maximum_materialized_plan_items": self.maximum_materialized_plan_items,
            "schema_version": self.schema_version,
        }


def _best_of(repetitions: int, operation: Any) -> tuple[Any, float]:
    best_value: Any = None
    best_seconds: float | None = None

    for _ in range(repetitions):
        started = perf_counter()
        value = operation()
        elapsed = perf_counter() - started

        if best_seconds is None or elapsed < best_seconds:
            best_value = value
            best_seconds = elapsed

    if best_seconds is None:
        raise RuntimeError("Benchmark operation did not execute.")

    return best_value, best_seconds * 1000.0


def _bounded_plan(active_items: int, capacity: int) -> tuple[int, int]:
    required_free_slots = max(0, active_items - capacity + 1)
    sample_size = min(required_free_slots, PLAN_SAMPLE_LIMIT)
    sample = tuple(range(sample_size))
    return required_free_slots, len(sample)


def run_capacity_saturation_benchmark(
    *,
    runtime_root: str | Path,
    configured_capacity: int = 50_000,
    repetitions: int = 3,
    scenarios: Iterable[int] = DEFAULT_SCENARIOS,
) -> CapacitySaturationReport:
    """Benchmark capacity calculations without materializing scenario items."""

    root = validate_external_runtime_root(runtime_root)

    if configured_capacity <= 0:
        raise ValueError("configured_capacity must be positive.")
    if repetitions <= 0:
        raise ValueError("repetitions must be positive.")

    scenario_values = tuple(int(value) for value in scenarios)
    if not scenario_values:
        raise ValueError("At least one scenario is required.")
    if any(value < 0 for value in scenario_values):
        raise ValueError("Scenario values must be non-negative.")

    existed_before = root.exists()
    results: list[CapacitySaturationResult] = []

    for active_items in scenario_values:
        tracemalloc.start()
        try:
            snapshot, status_ms = _best_of(
                repetitions,
                lambda: inspect_runtime_capacity(
                    runtime_root=root,
                    configured_capacity=configured_capacity,
                    simulated_active_items=active_items,
                ),
            )

            decision, decision_ms = _best_of(
                repetitions,
                lambda: (
                    snapshot.admission_allowed,
                    snapshot.available_slots,
                    snapshot.pressure_level.value,
                ),
            )

            plan, plan_ms = _best_of(
                repetitions,
                lambda: _bounded_plan(active_items, configured_capacity),
            )
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        required_free_slots, sample_size = plan
        admission_allowed, available_slots, pressure_level = decision

        results.append(
            CapacitySaturationResult(
                active_items=active_items,
                configured_capacity=configured_capacity,
                usage_ratio=snapshot.usage_ratio,
                pressure_level=pressure_level,
                admission_allowed=admission_allowed,
                available_slots=available_slots,
                required_free_slots=required_free_slots,
                bounded_plan_sample_size=sample_size,
                status_latency_ms=status_ms,
                decision_latency_ms=decision_ms,
                plan_latency_ms=plan_ms,
                peak_traced_bytes=peak_bytes,
            )
        )

    if root.exists() != existed_before:
        raise RuntimeError("The synthetic benchmark changed runtime existence.")

    return CapacitySaturationReport(
        benchmark_id="memorix_capacity_saturation",
        configured_capacity=configured_capacity,
        repetitions=repetitions,
        results=tuple(results),
    )
