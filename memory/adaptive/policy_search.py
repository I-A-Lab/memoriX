"""Deterministic bounded policy search for memoriX adaptive memory control.

This module evaluates retention-scoring and routing-policy candidates against a
small synthetic dataset. It does not train Titan, inspect or mutate runtime
storage, access the cold site, validate candidates, or execute pruning.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

from memory.adaptive.adaptive_routing_policy import (
    AdaptiveRoutingDecisionType,
    AdaptiveRoutingInput,
    AdaptiveRoutingPolicy,
    RoutingPruningCandidate,
    decide_adaptive_routing,
)
from memory.adaptive.retention_scoring import (
    RetentionScoringInput,
    RetentionScoringThresholds,
    RetentionScoringWeights,
    assess_adaptive_retention,
    calculate_adaptive_retention_score,
)


def _clamp_unit(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number))


@dataclass(frozen=True, slots=True)
class MemoryPolicyCandidate:
    """One complete retention and routing policy candidate."""

    policy_id: str
    retention_weights: RetentionScoringWeights
    retention_thresholds: RetentionScoringThresholds
    routing_policy: AdaptiveRoutingPolicy
    description: str = ""

    def validate(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must be a non-empty string.")
        self.retention_weights.validate()
        self.retention_thresholds.validate()
        self.routing_policy.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "description": self.description,
            "retention_weights": asdict(self.retention_weights),
            "retention_thresholds": asdict(self.retention_thresholds),
            "routing_policy": asdict(self.routing_policy),
        }


@dataclass(frozen=True, slots=True)
class MemoryPolicyEvaluationCase:
    """One reproducible synthetic expectation used during policy search."""

    case_id: str
    retention_input: RetentionScoringInput
    expected_retention_action: str
    routing_input: AdaptiveRoutingInput | None = None
    expected_routing_decision: AdaptiveRoutingDecisionType | None = None
    protected_safety_case: bool = False
    low_value_case: bool = False

    def validate(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must be a non-empty string.")
        self.retention_input.validate()
        if self.routing_input is not None:
            self.routing_input.validate()
        if (self.routing_input is None) != (self.expected_routing_decision is None):
            raise ValueError(
                "routing_input and expected_routing_decision must be provided together."
            )


@dataclass(frozen=True, slots=True)
class MemoryPolicyDataset:
    """Bounded synthetic dataset used by the deterministic evaluator."""

    cases: tuple[MemoryPolicyEvaluationCase, ...]
    dataset_id: str = "memorix-policy-dataset-v1"

    def validate(self) -> None:
        if not self.cases:
            raise ValueError("The policy dataset must contain at least one case.")
        seen: set[str] = set()
        for case in self.cases:
            case.validate()
            if case.case_id in seen:
                raise ValueError(f"Duplicate policy case_id: {case.case_id}")
            seen.add(case.case_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "case_count": len(self.cases),
            "case_ids": [case.case_id for case in self.cases],
        }


@dataclass(frozen=True, slots=True)
class MemoryPolicySearchSpace:
    """Finite and explicit list of policy candidates."""

    candidates: tuple[MemoryPolicyCandidate, ...]
    search_space_id: str = "memorix-policy-search-space-v1"

    def validate(self) -> None:
        if not self.candidates:
            raise ValueError("The policy search space must not be empty.")
        seen: set[str] = set()
        for candidate in self.candidates:
            candidate.validate()
            if candidate.policy_id in seen:
                raise ValueError(f"Duplicate policy_id: {candidate.policy_id}")
            seen.add(candidate.policy_id)


@dataclass(frozen=True, slots=True)
class MemoryPolicySearchConfig:
    """Bounded deterministic-search configuration."""

    max_trials: int = 32
    seed: int = 23

    def validate(self) -> None:
        if self.max_trials <= 0:
            raise ValueError("max_trials must be strictly positive.")
        if self.seed < 0:
            raise ValueError("seed must be non-negative.")


@dataclass(frozen=True, slots=True)
class MemoryPolicyMetrics:
    retention_accuracy: float
    routing_accuracy: float
    protected_memory_safety: float
    retention_efficiency: float
    stability: float
    complexity_penalty: float
    combined_score: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MemoryPolicyTrial:
    trial_index: int
    policy: MemoryPolicyCandidate
    metrics: MemoryPolicyMetrics
    passed_case_ids: tuple[str, ...]
    failed_case_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    dry_run: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    pruning_executed: bool = False
    candidate_validated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "policy": self.policy.to_dict(),
            "metrics": self.metrics.to_dict(),
            "passed_case_ids": list(self.passed_case_ids),
            "failed_case_ids": list(self.failed_case_ids),
            "reasons": list(self.reasons),
            "dry_run": self.dry_run,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
            "pruning_executed": self.pruning_executed,
            "candidate_validated": self.candidate_validated,
        }


@dataclass(frozen=True, slots=True)
class MemoryPolicySearchResult:
    search_space_id: str
    dataset_id: str
    seed: int
    trial_count: int
    best_policy: MemoryPolicyCandidate
    best_score: float
    trials: tuple[MemoryPolicyTrial, ...]
    selection_reasons: tuple[str, ...]
    difference_from_default: Mapping[str, float]
    dry_run: bool = True
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    pruning_executed: bool = False
    candidate_validated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "search_space_id": self.search_space_id,
            "dataset_id": self.dataset_id,
            "seed": self.seed,
            "trial_count": self.trial_count,
            "best_policy": self.best_policy.to_dict(),
            "best_score": self.best_score,
            "trials": [trial.to_dict() for trial in self.trials],
            "selection_reasons": list(self.selection_reasons),
            "difference_from_default": dict(self.difference_from_default),
            "dry_run": self.dry_run,
            "runtime_modified": self.runtime_modified,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
            "pruning_executed": self.pruning_executed,
            "candidate_validated": self.candidate_validated,
        }


def default_memory_policy_dataset() -> MemoryPolicyDataset:
    """Return a compact dataset covering retention, protection, and routing."""

    prunable = (
        RoutingPruningCandidate(memory_id="old-low", retention_score=0.05),
    )
    cases = (
        MemoryPolicyEvaluationCase(
            case_id="important-memory-kept",
            retention_input=RetentionScoringInput(
                memory_id="important", age_days=3, access_count=18,
                importance=1.0, retrieval_score=0.95, confidence=0.95,
                momentum=0.8, surprise=0.6,
            ),
            expected_retention_action="keep",
        ),
        MemoryPolicyEvaluationCase(
            case_id="recent-memory-kept",
            retention_input=RetentionScoringInput(
                memory_id="recent", age_days=0, access_count=4,
                importance=0.65, retrieval_score=0.75, confidence=0.8,
                momentum=0.5, surprise=0.4,
            ),
            expected_retention_action="keep",
        ),
        MemoryPolicyEvaluationCase(
            case_id="obsolete-memory-deactivated",
            retention_input=RetentionScoringInput(
                memory_id="obsolete", age_days=730, access_count=0,
                importance=0.0, retrieval_score=0.0, confidence=0.1,
                momentum=0.0, surprise=0.0, replaced=True,
            ),
            expected_retention_action="deactivate_candidate",
            low_value_case=True,
        ),
        MemoryPolicyEvaluationCase(
            case_id="inactive-memory-preserved-inactive",
            retention_input=RetentionScoringInput(
                memory_id="inactive", age_days=400, access_count=0,
                importance=0.1, retrieval_score=0.1, confidence=0.2,
                active=False,
            ),
            expected_retention_action="keep_inactive",
            low_value_case=True,
        ),
        MemoryPolicyEvaluationCase(
            case_id="protected-memory-safe",
            retention_input=RetentionScoringInput(
                memory_id="protected", age_days=900, access_count=0,
                importance=0.0, retrieval_score=0.0, confidence=0.0,
                protected=True, replaced=True,
            ),
            expected_retention_action="keep_protected",
            protected_safety_case=True,
        ),
        MemoryPolicyEvaluationCase(
            case_id="strong-candidate-admitted",
            retention_input=RetentionScoringInput(
                memory_id="strong-candidate", age_days=0, access_count=8,
                importance=0.95, retrieval_score=0.85, confidence=0.95,
                momentum=0.7, surprise=0.7,
            ),
            expected_retention_action="keep",
            routing_input=AdaptiveRoutingInput(
                target_id="strong-candidate", configured_capacity=10,
                active_memories=7, importance=0.95, confidence=0.95,
            ),
            expected_routing_decision=AdaptiveRoutingDecisionType.ADMIT,
        ),
        MemoryPolicyEvaluationCase(
            case_id="weak-candidate-deferred-at-capacity",
            retention_input=RetentionScoringInput(
                memory_id="weak-candidate", age_days=365, access_count=0,
                importance=0.1, retrieval_score=0.1, confidence=0.2,
                momentum=0.0, surprise=0.0,
            ),
            expected_retention_action="deactivate_candidate",
            routing_input=AdaptiveRoutingInput(
                target_id="weak-candidate", configured_capacity=10,
                active_memories=10, importance=0.1, confidence=0.2,
            ),
            expected_routing_decision=AdaptiveRoutingDecisionType.DEFER,
            low_value_case=True,
        ),
        MemoryPolicyEvaluationCase(
            case_id="strong-candidate-plans-pruning",
            retention_input=RetentionScoringInput(
                memory_id="priority-candidate", age_days=0, access_count=12,
                importance=1.0, retrieval_score=0.9, confidence=0.95,
                momentum=0.8, surprise=0.8,
            ),
            expected_retention_action="keep",
            routing_input=AdaptiveRoutingInput(
                target_id="priority-candidate", configured_capacity=10,
                active_memories=10, importance=1.0, confidence=0.95,
                pruning_candidates=prunable,
            ),
            expected_routing_decision=(
                AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING
            ),
        ),
        MemoryPolicyEvaluationCase(
            case_id="pending-candidate-deferred",
            retention_input=RetentionScoringInput(
                memory_id="pending", age_days=0, access_count=5,
                importance=0.9, retrieval_score=0.8, confidence=0.9,
            ),
            expected_retention_action="keep",
            routing_input=AdaptiveRoutingInput(
                target_id="pending", configured_capacity=10,
                active_memories=2, human_validated=False,
            ),
            expected_routing_decision=AdaptiveRoutingDecisionType.DEFER,
            protected_safety_case=True,
        ),
    )
    dataset = MemoryPolicyDataset(cases=cases)
    dataset.validate()
    return dataset


def default_memory_policy_search_space() -> MemoryPolicySearchSpace:
    """Return a bounded 4x3 deterministic grid of policy candidates."""

    weight_profiles = (
        ("balanced", RetentionScoringWeights()),
        ("importance", RetentionScoringWeights(
            importance=0.35, recency=0.15, usage=0.10, retrieval=0.15,
            confidence=0.10, momentum=0.10, surprise=0.05,
        )),
        ("usage", RetentionScoringWeights(
            importance=0.20, recency=0.20, usage=0.25, retrieval=0.15,
            confidence=0.10, momentum=0.05, surprise=0.05,
        )),
        ("retrieval", RetentionScoringWeights(
            importance=0.20, recency=0.15, usage=0.10, retrieval=0.25,
            confidence=0.15, momentum=0.10, surprise=0.05,
        )),
    )
    threshold_profiles = (
        (
            "default",
            RetentionScoringThresholds(),
            AdaptiveRoutingPolicy(),
        ),
        (
            "conservative",
            RetentionScoringThresholds(keep=0.70, watch=0.50, review=0.30),
            AdaptiveRoutingPolicy(
                minimum_admission_score=0.50,
                high_priority_score=0.70,
                soft_pruning_score=0.30,
            ),
        ),
        (
            "permissive",
            RetentionScoringThresholds(keep=0.60, watch=0.40, review=0.20),
            AdaptiveRoutingPolicy(
                minimum_admission_score=0.40,
                high_priority_score=0.60,
                soft_pruning_score=0.20,
            ),
        ),
    )
    candidates = tuple(
        MemoryPolicyCandidate(
            policy_id=f"{weight_name}-{threshold_name}",
            retention_weights=weights,
            retention_thresholds=thresholds,
            routing_policy=routing,
            description=(
                f"{weight_name} retention weights with "
                f"{threshold_name} decision thresholds."
            ),
        )
        for weight_name, weights in weight_profiles
        for threshold_name, thresholds, routing in threshold_profiles
    )
    search_space = MemoryPolicySearchSpace(candidates=candidates)
    search_space.validate()
    return search_space


def _policy_distance_from_default(candidate: MemoryPolicyCandidate) -> float:
    default = MemoryPolicyCandidate(
        policy_id="default",
        retention_weights=RetentionScoringWeights(),
        retention_thresholds=RetentionScoringThresholds(),
        routing_policy=AdaptiveRoutingPolicy(),
    )
    values: list[float] = []
    for current, baseline in (
        (asdict(candidate.retention_weights), asdict(default.retention_weights)),
        (asdict(candidate.retention_thresholds), asdict(default.retention_thresholds)),
        (asdict(candidate.routing_policy), asdict(default.routing_policy)),
    ):
        for key in sorted(current):
            if key == "maximum_pruning_items":
                continue
            values.append(abs(float(current[key]) - float(baseline[key])))
    return _clamp_unit(sum(values) / max(1, len(values)))


def evaluate_memory_policy(
    candidate: MemoryPolicyCandidate,
    dataset: MemoryPolicyDataset,
    *,
    trial_index: int = 1,
) -> MemoryPolicyTrial:
    """Evaluate one policy without any runtime or model side effect."""

    candidate.validate()
    dataset.validate()
    passed: list[str] = []
    failed: list[str] = []
    retention_correct = 0
    routing_correct = 0
    routing_total = 0
    protected_correct = 0
    protected_total = 0
    low_value_correct = 0
    low_value_total = 0
    stable = True

    for case in dataset.cases:
        first = assess_adaptive_retention(
            case.retention_input,
            weights=candidate.retention_weights,
            thresholds=candidate.retention_thresholds,
            assessment_id=f"trial-{trial_index}-{case.case_id}",
        )
        second_score, _ = calculate_adaptive_retention_score(
            case.retention_input,
            weights=candidate.retention_weights,
        )
        stable = stable and math.isclose(
            first.retention_score, second_score, rel_tol=0.0, abs_tol=1e-12
        )
        case_passed = first.recommended_action == case.expected_retention_action
        retention_correct += int(case_passed)

        if case.low_value_case:
            low_value_total += 1
            low_value_correct += int(
                first.recommended_action
                in {"deactivate_candidate", "keep_inactive", "review_for_soft_pruning"}
            )

        if case.protected_safety_case:
            protected_total += 1
            protected_correct += int(first.protected)

        if case.routing_input is not None:
            routing_total += 1
            routed = decide_adaptive_routing(
                replace(
                    case.routing_input,
                    retention_score=first.retention_score,
                ),
                policy=candidate.routing_policy,
                decision_id=f"trial-{trial_index}-{case.case_id}",
            )
            routing_ok = routed.decision is case.expected_routing_decision
            routing_correct += int(routing_ok)
            case_passed = case_passed and routing_ok
            if case.protected_safety_case:
                protected_correct += int(
                    routed.decision
                    in {
                        AdaptiveRoutingDecisionType.DEFER,
                        AdaptiveRoutingDecisionType.PROTECT,
                    }
                )
                protected_total += 1

        (passed if case_passed else failed).append(case.case_id)

    retention_accuracy = retention_correct / len(dataset.cases)
    routing_accuracy = routing_correct / routing_total if routing_total else 1.0
    protected_safety = protected_correct / protected_total if protected_total else 1.0
    retention_efficiency = low_value_correct / low_value_total if low_value_total else 1.0
    stability_score = 1.0 if stable else 0.0
    complexity_penalty = _policy_distance_from_default(candidate)
    combined_score = _clamp_unit(
        0.30 * retention_accuracy
        + 0.30 * routing_accuracy
        + 0.15 * protected_safety
        + 0.10 * retention_efficiency
        + 0.15 * stability_score
        - 0.05 * complexity_penalty
    )
    metrics = MemoryPolicyMetrics(
        retention_accuracy=retention_accuracy,
        routing_accuracy=routing_accuracy,
        protected_memory_safety=protected_safety,
        retention_efficiency=retention_efficiency,
        stability=stability_score,
        complexity_penalty=complexity_penalty,
        combined_score=combined_score,
    )
    reasons = (
        f"retention_accuracy={retention_accuracy:.4f}",
        f"routing_accuracy={routing_accuracy:.4f}",
        f"protected_memory_safety={protected_safety:.4f}",
        f"retention_efficiency={retention_efficiency:.4f}",
        f"stability={stability_score:.4f}",
        f"complexity_penalty={complexity_penalty:.4f}",
    )
    return MemoryPolicyTrial(
        trial_index=trial_index,
        policy=candidate,
        metrics=metrics,
        passed_case_ids=tuple(passed),
        failed_case_ids=tuple(failed),
        reasons=reasons,
    )


def _ordered_candidates(
    candidates: Sequence[MemoryPolicyCandidate],
    seed: int,
) -> tuple[MemoryPolicyCandidate, ...]:
    ordered = tuple(sorted(candidates, key=lambda item: item.policy_id))
    if not ordered:
        return ()
    offset = seed % len(ordered)
    return ordered[offset:] + ordered[:offset]


def _difference_from_default(candidate: MemoryPolicyCandidate) -> dict[str, float]:
    default_weights = asdict(RetentionScoringWeights())
    candidate_weights = asdict(candidate.retention_weights)
    result = {
        f"retention_weights.{key}": float(candidate_weights[key]) - float(default_weights[key])
        for key in sorted(default_weights)
    }
    default_thresholds = asdict(RetentionScoringThresholds())
    candidate_thresholds = asdict(candidate.retention_thresholds)
    result.update(
        {
            f"retention_thresholds.{key}": float(candidate_thresholds[key]) - float(default_thresholds[key])
            for key in sorted(default_thresholds)
        }
    )
    default_routing = asdict(AdaptiveRoutingPolicy())
    candidate_routing = asdict(candidate.routing_policy)
    result.update(
        {
            f"routing_policy.{key}": float(candidate_routing[key]) - float(default_routing[key])
            for key in sorted(default_routing)
            if key != "maximum_pruning_items"
        }
    )
    return result


def search_memory_policies(
    *,
    search_space: MemoryPolicySearchSpace | None = None,
    dataset: MemoryPolicyDataset | None = None,
    config: MemoryPolicySearchConfig | None = None,
) -> MemoryPolicySearchResult:
    """Run a finite deterministic search and return ranked trial details."""

    resolved_space = search_space or default_memory_policy_search_space()
    resolved_dataset = dataset or default_memory_policy_dataset()
    resolved_config = config or MemoryPolicySearchConfig()
    resolved_space.validate()
    resolved_dataset.validate()
    resolved_config.validate()

    selected = _ordered_candidates(
        resolved_space.candidates,
        resolved_config.seed,
    )[: resolved_config.max_trials]
    trials = tuple(
        evaluate_memory_policy(candidate, resolved_dataset, trial_index=index)
        for index, candidate in enumerate(selected, start=1)
    )
    ranked = tuple(
        sorted(
            trials,
            key=lambda trial: (
                -trial.metrics.combined_score,
                trial.metrics.complexity_penalty,
                trial.policy.policy_id,
            ),
        )
    )
    best = ranked[0]
    selection_reasons = (
        "highest_combined_score",
        "protected_memory_safety_is_weighted",
        "routing_and_retention_are_evaluated_together",
        "lower_complexity_breaks_equal_scores",
        "policy_id_breaks_remaining_ties_deterministically",
    )
    return MemoryPolicySearchResult(
        search_space_id=resolved_space.search_space_id,
        dataset_id=resolved_dataset.dataset_id,
        seed=resolved_config.seed,
        trial_count=len(ranked),
        best_policy=best.policy,
        best_score=best.metrics.combined_score,
        trials=ranked,
        selection_reasons=selection_reasons,
        difference_from_default=_difference_from_default(best.policy),
    )
