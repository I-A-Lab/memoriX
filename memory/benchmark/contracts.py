"""Contracts for isolated adaptive-memory design benchmarks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class BenchmarkDesign(str, Enum):
    """Memory designs compared by the isolated benchmark."""

    BASELINE = "baseline"
    PRESSURE = "pressure"
    TOPIC_BLOCKS = "topic_blocks"
    DYNAMIC_CAPACITY = "dynamic_capacity"
    ADAPTIVE_CONTROLLER = "adaptive_controller"


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    """One deterministic synthetic benchmark scenario."""

    scenario_id: str
    scope_id: str
    capacity: int
    used_items: int
    usage_samples: tuple[int, ...]
    term_frequencies: Mapping[str, int]
    surprise_samples: tuple[float, ...]
    previous_pressure_samples: tuple[float, ...]
    documents: tuple[str, ...]
    expected_pressure: str
    expected_expand: bool
    expected_pruning_actions: bool

    def validate(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError(
                "scenario_id must be non-empty."
            )

        if not self.scope_id.strip():
            raise ValueError(
                "scope_id must be non-empty."
            )

        if self.capacity <= 0:
            raise ValueError(
                "capacity must be positive."
            )

        if self.used_items < 0:
            raise ValueError(
                "used_items must be non-negative."
            )

        if not self.documents:
            raise ValueError(
                "At least one synthetic document is required."
            )


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    """Metrics produced for one design and one scenario."""

    latency_ms: float
    pressure_score: float | None
    topic_block_count: int
    expansion_recommended: bool
    pruning_recommendation_count: int
    safety_contracts_preserved: bool
    expected_behavior_matched: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Result of one design on one synthetic scenario."""

    design: BenchmarkDesign
    scenario_id: str
    metrics: BenchmarkMetrics
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "design": self.design.value,
            "scenario_id": self.scenario_id,
            "metrics": self.metrics.to_dict(),
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    """Aggregate benchmark report."""

    benchmark_id: str
    seed: int
    results: tuple[BenchmarkResult, ...]
    ranking: tuple[str, ...]
    created_at: str
    synthetic_data_only: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    actions_applied: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "seed": self.seed,
            "results": [
                result.to_dict()
                for result in self.results
            ],
            "ranking": list(self.ranking),
            "created_at": self.created_at,
            "synthetic_data_only": (
                self.synthetic_data_only
            ),
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "actions_applied": self.actions_applied,
            "schema_version": self.schema_version,
        }
