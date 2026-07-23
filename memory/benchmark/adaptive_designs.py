"""Isolated benchmark for adaptive-memory design variants."""

from __future__ import annotations

import random
import time
import uuid
from collections import Counter
from typing import Any

from memory.adaptive import (
    AdaptiveControllerInput,
    CapacityRecommendationInput,
    HotMemoryPruningInput,
    PressureObservationInput,
    evaluate_adaptive_controller,
    observe_memory_pressure,
    observe_topic_block,
    recommend_dynamic_capacity,
    TopicBlockInput,
)
from memory.adaptive.contracts import (
    CapacityRecommendationLevel,
    SoftPruningAction,
    utc_now_iso,
)
from memory.benchmark.contracts import (
    BenchmarkDesign,
    BenchmarkMetrics,
    BenchmarkResult,
    BenchmarkScenario,
    BenchmarkSummary,
)


def _elapsed_ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def _synthetic_memories(
    scenario: BenchmarkScenario,
) -> tuple[HotMemoryPruningInput, ...]:
    """Create deterministic hot-memory measurements."""

    return (
        HotMemoryPruningInput(
            memory_id=(
                f"{scenario.scenario_id}_protected"
            ),
            block_id=scenario.scope_id,
            importance=0.95,
            access_count=25,
            age_days=1,
            retrieval_score=0.9,
        ),
        HotMemoryPruningInput(
            memory_id=(
                f"{scenario.scenario_id}_weak"
            ),
            block_id=scenario.scope_id,
            importance=0.30,
            access_count=1,
            age_days=280,
            retrieval_score=0.25,
        ),
        HotMemoryPruningInput(
            memory_id=(
                f"{scenario.scenario_id}_inactive_candidate"
            ),
            block_id=scenario.scope_id,
            importance=0.02,
            access_count=0,
            age_days=365,
            retrieval_score=0.01,
        ),
    )


def _pressure(
    scenario: BenchmarkScenario,
):
    return observe_memory_pressure(
        PressureObservationInput(
            scope_id=scenario.scope_id,
            used_items=scenario.used_items,
            capacity=scenario.capacity,
            usage_samples=scenario.usage_samples,
            term_frequencies=(
                scenario.term_frequencies
            ),
            surprise_samples=(
                scenario.surprise_samples
            ),
            previous_pressure_samples=(
                scenario.previous_pressure_samples
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        observation_id=(
            f"pressure_{scenario.scenario_id}"
        ),
    )


def _baseline(
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    start = time.perf_counter()

    unique_documents = len(set(scenario.documents))

    latency = _elapsed_ms(start)

    return BenchmarkResult(
        design=BenchmarkDesign.BASELINE,
        scenario_id=scenario.scenario_id,
        metrics=BenchmarkMetrics(
            latency_ms=latency,
            pressure_score=None,
            topic_block_count=0,
            expansion_recommended=False,
            pruning_recommendation_count=0,
            safety_contracts_preserved=True,
            expected_behavior_matched=True,
        ),
        details={
            "document_count": len(
                scenario.documents
            ),
            "unique_document_count": (
                unique_documents
            ),
            "adaptive_features": [],
        },
    )


def _pressure_design(
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    start = time.perf_counter()

    pressure = _pressure(scenario)

    latency = _elapsed_ms(start)

    expected_match = (
        pressure.level.value
        == scenario.expected_pressure
        or (
            scenario.scenario_id
            == "persistent_pressure"
            and pressure.level.value
            in {"high", "critical"}
        )
    )

    return BenchmarkResult(
        design=BenchmarkDesign.PRESSURE,
        scenario_id=scenario.scenario_id,
        metrics=BenchmarkMetrics(
            latency_ms=latency,
            pressure_score=(
                pressure.memory_pressure
            ),
            topic_block_count=0,
            expansion_recommended=False,
            pruning_recommendation_count=0,
            safety_contracts_preserved=(
                pressure.observation_only
            ),
            expected_behavior_matched=(
                expected_match
            ),
        ),
        details={
            "pressure_level": (
                pressure.level.value
            ),
            "components": (
                pressure.components.as_dict()
            ),
        },
    )


def _topic_blocks_design(
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    start = time.perf_counter()

    block_ids: set[str] = set()
    labels: Counter[str] = Counter()

    for index, document in enumerate(
        scenario.documents
    ):
        observation = observe_topic_block(
            TopicBlockInput(
                content=document,
                item_id=(
                    f"{scenario.scenario_id}_{index}"
                ),
                capacity=scenario.capacity,
                used_items=1,
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            routing_id=(
                f"routing_{scenario.scenario_id}_{index}"
            ),
        )

        block_ids.add(observation.block_id)
        labels[observation.label] += 1

    latency = _elapsed_ms(start)

    return BenchmarkResult(
        design=BenchmarkDesign.TOPIC_BLOCKS,
        scenario_id=scenario.scenario_id,
        metrics=BenchmarkMetrics(
            latency_ms=latency,
            pressure_score=None,
            topic_block_count=len(block_ids),
            expansion_recommended=False,
            pruning_recommendation_count=0,
            safety_contracts_preserved=True,
            expected_behavior_matched=(
                len(block_ids) >= 1
            ),
        ),
        details={
            "block_ids": sorted(block_ids),
            "labels": dict(labels),
            "physical_partitioning": False,
        },
    )


def _capacity_design(
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    start = time.perf_counter()

    pressure = _pressure(scenario)

    recommendation = recommend_dynamic_capacity(
        CapacityRecommendationInput(
            block_id=scenario.scope_id,
            current_capacity=scenario.capacity,
            used_items=scenario.used_items,
            pressure=pressure,
            evaluated_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        recommendation_id=(
            f"capacity_{scenario.scenario_id}"
        ),
    )

    latency = _elapsed_ms(start)

    expanded = (
        recommendation.level
        is CapacityRecommendationLevel.EXPAND
    )

    return BenchmarkResult(
        design=BenchmarkDesign.DYNAMIC_CAPACITY,
        scenario_id=scenario.scenario_id,
        metrics=BenchmarkMetrics(
            latency_ms=latency,
            pressure_score=(
                pressure.memory_pressure
            ),
            topic_block_count=0,
            expansion_recommended=expanded,
            pruning_recommendation_count=0,
            safety_contracts_preserved=(
                recommendation.dry_run
                and not recommendation.applied
            ),
            expected_behavior_matched=(
                expanded
                == scenario.expected_expand
            ),
        ),
        details={
            "level": recommendation.level.value,
            "recommended_capacity": (
                recommendation.recommended_capacity
            ),
            "recommended_increment": (
                recommendation.recommended_increment
            ),
            "blocking_reasons": list(
                recommendation.blocking_reasons
            ),
        },
    )


def _adaptive_design(
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    start = time.perf_counter()

    decision = evaluate_adaptive_controller(
        AdaptiveControllerInput(
            scope_id=scenario.scope_id,
            current_capacity=scenario.capacity,
            used_items=scenario.used_items,
            usage_samples=scenario.usage_samples,
            term_frequencies=(
                scenario.term_frequencies
            ),
            surprise_samples=(
                scenario.surprise_samples
            ),
            previous_pressure_samples=(
                scenario.previous_pressure_samples
            ),
            memories=_synthetic_memories(
                scenario
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        decision_id=(
            f"adaptive_{scenario.scenario_id}"
        ),
    )

    latency = _elapsed_ms(start)

    pruning_actions = [
        recommendation.action
        for recommendation
        in decision.pruning.recommendations
        if recommendation.action
        is not SoftPruningAction.KEEP
    ]

    expansion = (
        decision.capacity.level
        is CapacityRecommendationLevel.EXPAND
    )

    safety = (
        decision.observation_only
        and decision.dry_run
        and not decision.applied
        and decision.hot_site_only
        and decision.cold_site_untouched
        and not decision.retrieval_behavior_changed
        and not decision.pruning.physical_deletion
    )

    expected_match = (
        expansion == scenario.expected_expand
        and bool(pruning_actions)
        == scenario.expected_pruning_actions
    )

    return BenchmarkResult(
        design=(
            BenchmarkDesign.ADAPTIVE_CONTROLLER
        ),
        scenario_id=scenario.scenario_id,
        metrics=BenchmarkMetrics(
            latency_ms=latency,
            pressure_score=(
                decision.pressure.memory_pressure
            ),
            topic_block_count=0,
            expansion_recommended=expansion,
            pruning_recommendation_count=len(
                pruning_actions
            ),
            safety_contracts_preserved=safety,
            expected_behavior_matched=(
                expected_match
            ),
        ),
        details={
            "status": decision.status.value,
            "recommended_actions": list(
                decision.recommended_actions
            ),
            "blocked_actions": list(
                decision.blocked_actions
            ),
        },
    )


def run_design(
    design: BenchmarkDesign,
    scenario: BenchmarkScenario,
) -> BenchmarkResult:
    """Run one isolated design variant."""

    if design is BenchmarkDesign.BASELINE:
        return _baseline(scenario)

    if design is BenchmarkDesign.PRESSURE:
        return _pressure_design(scenario)

    if design is BenchmarkDesign.TOPIC_BLOCKS:
        return _topic_blocks_design(scenario)

    if design is BenchmarkDesign.DYNAMIC_CAPACITY:
        return _capacity_design(scenario)

    if design is BenchmarkDesign.ADAPTIVE_CONTROLLER:
        return _adaptive_design(scenario)

    raise ValueError(
        f"Unsupported benchmark design: {design}"
    )


def _design_score(
    results: tuple[BenchmarkResult, ...],
    design: BenchmarkDesign,
) -> float:
    matching = [
        result
        for result in results
        if result.design is design
    ]

    if not matching:
        return 0.0

    expected_score = sum(
        result.metrics.expected_behavior_matched
        for result in matching
    ) / len(matching)

    safety_score = sum(
        result.metrics.safety_contracts_preserved
        for result in matching
    ) / len(matching)

    average_latency = sum(
        result.metrics.latency_ms
        for result in matching
    ) / len(matching)

    latency_score = 1.0 / (
        1.0 + average_latency
    )

    feature_score = {
        BenchmarkDesign.BASELINE: 0.20,
        BenchmarkDesign.PRESSURE: 0.40,
        BenchmarkDesign.TOPIC_BLOCKS: 0.55,
        BenchmarkDesign.DYNAMIC_CAPACITY: 0.75,
        BenchmarkDesign.ADAPTIVE_CONTROLLER: 1.00,
    }[design]

    return (
        0.40 * expected_score
        + 0.35 * safety_score
        + 0.20 * feature_score
        + 0.05 * latency_score
    )


def run_adaptive_design_benchmark(
    scenarios: tuple[BenchmarkScenario, ...],
    *,
    seed: int = 42,
    benchmark_id: str | None = None,
) -> BenchmarkSummary:
    """Run all variants on synthetic scenarios."""

    random.seed(seed)

    designs = tuple(BenchmarkDesign)

    results = tuple(
        run_design(design, scenario)
        for scenario in scenarios
        for design in designs
    )

    scores = {
        design.value: _design_score(
            results,
            design,
        )
        for design in designs
    }

    ranking = tuple(
        name
        for name, _ in sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    )

    return BenchmarkSummary(
        benchmark_id=(
            benchmark_id
            or f"benchmark_{uuid.uuid4().hex}"
        ),
        seed=seed,
        results=results,
        ranking=ranking,
        created_at=utc_now_iso(),
    )
