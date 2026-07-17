"""Deterministic adaptive retention scoring and hot-site ranking.

This module scores explicit hot-memory measurements only. It does not read or
write runtime storage, access the cold site, apply pruning, or load Titan.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import asdict, dataclass
from statistics import fmean
from typing import Any, Iterable, Mapping

from memory.adaptive.contracts import utc_now_iso
from memory.adaptive.memory_pressure import normalize_age, normalize_low_usage, normalize_unit


@dataclass(frozen=True, slots=True)
class RetentionScoringWeights:
    importance: float = 0.25
    recency: float = 0.20
    usage: float = 0.15
    retrieval: float = 0.15
    confidence: float = 0.10
    momentum: float = 0.10
    surprise: float = 0.05
    inactive_penalty: float = 0.20
    replaced_penalty: float = 0.25

    def validate(self) -> None:
        values = asdict(self)
        if any(not math.isfinite(value) or value < 0.0 for value in values.values()):
            raise ValueError("Retention-scoring weights must be finite and non-negative.")
        positive_weights = (
            self.importance
            + self.recency
            + self.usage
            + self.retrieval
            + self.confidence
            + self.momentum
            + self.surprise
        )
        if positive_weights <= 0.0:
            raise ValueError("At least one positive retention weight must be set.")


@dataclass(frozen=True, slots=True)
class RetentionScoringThresholds:
    keep: float = 0.65
    watch: float = 0.45
    review: float = 0.25

    def validate(self) -> None:
        values = (self.keep, self.watch, self.review)
        if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
            raise ValueError("Retention thresholds must be finite values between 0 and 1.")
        if not self.review <= self.watch <= self.keep:
            raise ValueError("Retention thresholds must satisfy review <= watch <= keep.")


@dataclass(frozen=True, slots=True)
class RetentionScoringInput:
    memory_id: str
    age_days: float = 0.0
    access_count: int = 0
    importance: float = 0.5
    retrieval_score: float = 0.5
    confidence: float = 0.5
    momentum: float = 0.0
    surprise: float = 0.0
    active: bool = True
    replaced: bool = False
    protected: bool = False
    pinned: bool = False
    human_validated: bool = True
    metadata: Mapping[str, Any] | None = None
    observed_at: str | None = None

    def validate(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must be a non-empty string.")
        if self.access_count < 0:
            raise ValueError("access_count must be non-negative.")
        if self.age_days < 0.0:
            raise ValueError("age_days must be non-negative.")


@dataclass(frozen=True, slots=True)
class RetentionScoreComponents:
    importance: float
    recency: float
    usage: float
    retrieval: float
    confidence: float
    momentum: float
    surprise: float
    inactive_penalty: float
    replaced_penalty: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RetentionScoreAssessment:
    assessment_id: str
    memory_id: str
    observed_at: str
    retention_score: float
    pressure_score: float
    rank: int | None
    recommended_action: str
    protected: bool
    protection_reasons: tuple[str, ...]
    reasons: tuple[str, ...]
    risk_reasons: tuple[str, ...]
    explanation: tuple[str, ...]
    components: RetentionScoreComponents
    schema_version: int = 1
    observation_only: bool = True
    dry_run: bool = True
    applied: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "memory_id": self.memory_id,
            "observed_at": self.observed_at,
            "retention_score": self.retention_score,
            "pressure_score": self.pressure_score,
            "rank": self.rank,
            "recommended_action": self.recommended_action,
            "protected": self.protected,
            "protection_reasons": list(self.protection_reasons),
            "reasons": list(self.reasons),
            "risk_reasons": list(self.risk_reasons),
            "explanation": list(self.explanation),
            "components": self.components.to_dict(),
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
        }


@dataclass(frozen=True, slots=True)
class HotSiteRetentionRanking:
    ranking_id: str
    observed_at: str
    memory_count: int
    mean_retention: float
    maximum_retention: float
    minimum_retention: float
    protected_count: int
    action_counts: Mapping[str, int]
    assessments: tuple[RetentionScoreAssessment, ...]
    schema_version: int = 1
    observation_only: bool = True
    dry_run: bool = True
    applied: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranking_id": self.ranking_id,
            "observed_at": self.observed_at,
            "memory_count": self.memory_count,
            "mean_retention": self.mean_retention,
            "maximum_retention": self.maximum_retention,
            "minimum_retention": self.minimum_retention,
            "protected_count": self.protected_count,
            "action_counts": dict(self.action_counts),
            "assessments": [assessment.to_dict() for assessment in self.assessments],
            "schema_version": self.schema_version,
            "observation_only": self.observation_only,
            "dry_run": self.dry_run,
            "applied": self.applied,
            "cold_site_accessed": self.cold_site_accessed,
            "neural_model_loaded": self.neural_model_loaded,
        }


def calculate_adaptive_retention_score(
    source: RetentionScoringInput,
    *,
    weights: RetentionScoringWeights | None = None,
    age_horizon_days: float = 365.0,
    usage_saturation_count: float = 20.0,
) -> tuple[float, RetentionScoreComponents]:
    """Return one normalized score and its fully explainable components."""

    source.validate()
    resolved_weights = weights or RetentionScoringWeights()
    resolved_weights.validate()

    components = RetentionScoreComponents(
        importance=normalize_unit(source.importance, default=0.5),
        recency=1.0 - normalize_age(source.age_days, horizon_days=age_horizon_days),
        usage=1.0 - normalize_low_usage(source.access_count, saturation_count=usage_saturation_count),
        retrieval=normalize_unit(source.retrieval_score, default=0.5),
        confidence=normalize_unit(source.confidence, default=0.5),
        momentum=normalize_unit(source.momentum),
        surprise=normalize_unit(source.surprise),
        inactive_penalty=0.0 if source.active else 1.0,
        replaced_penalty=1.0 if source.replaced else 0.0,
    )
    values = components.to_dict()
    positive_names = ("importance", "recency", "usage", "retrieval", "confidence", "momentum", "surprise")
    positive_weight = sum(getattr(resolved_weights, name) for name in positive_names)
    score = sum(values[name] * getattr(resolved_weights, name) for name in positive_names) / positive_weight
    score -= components.inactive_penalty * resolved_weights.inactive_penalty
    score -= components.replaced_penalty * resolved_weights.replaced_penalty
    return normalize_unit(score), components


def assess_adaptive_retention(
    source: RetentionScoringInput,
    *,
    weights: RetentionScoringWeights | None = None,
    thresholds: RetentionScoringThresholds | None = None,
    age_horizon_days: float = 365.0,
    usage_saturation_count: float = 20.0,
    assessment_id: str | None = None,
    rank: int | None = None,
) -> RetentionScoreAssessment:
    """Create one deterministic, action-free retention assessment."""

    resolved_thresholds = thresholds or RetentionScoringThresholds()
    resolved_thresholds.validate()
    score, components = calculate_adaptive_retention_score(
        source,
        weights=weights,
        age_horizon_days=age_horizon_days,
        usage_saturation_count=usage_saturation_count,
    )

    protection_reasons = tuple(
        reason
        for reason, enabled in (
            ("explicitly_protected", source.protected),
            ("pinned", source.pinned),
            ("not_human_validated", not source.human_validated),
        )
        if enabled
    )
    protected = bool(protection_reasons)

    positive_labels = {
        "importance": "high_importance",
        "recency": "recent",
        "usage": "frequently_accessed",
        "retrieval": "strong_retrieval",
        "confidence": "high_confidence",
        "momentum": "strong_momentum",
        "surprise": "high_surprise",
    }
    risk_labels = {
        "importance": "low_importance",
        "recency": "old",
        "usage": "rarely_accessed",
        "retrieval": "weak_retrieval",
        "confidence": "low_confidence",
        "momentum": "low_momentum",
        "surprise": "low_surprise",
    }
    component_values = components.to_dict()
    reasons = tuple(
        positive_labels[name]
        for name in sorted(positive_labels)
        if component_values[name] >= 0.75
    )
    risk_reasons = tuple(
        [
            risk_labels[name]
            for name in sorted(risk_labels)
            if component_values[name] <= 0.25
        ]
        + (["inactive"] if not source.active else [])
        + (["replaced"] if source.replaced else [])
    )

    if protected:
        action = "keep_protected"
    elif not source.active:
        action = "keep_inactive"
    elif score >= resolved_thresholds.keep:
        action = "keep"
    elif score >= resolved_thresholds.watch:
        action = "watch"
    elif score >= resolved_thresholds.review:
        action = "review_for_soft_pruning"
    else:
        action = "deactivate_candidate"

    explanation = (
        f"retention_score={score:.4f}, pressure_score={1.0 - score:.4f}.",
        f"recommended_action={action}.",
        "The result is deterministic, observation-only, and no memory mutation was applied.",
        "The cold site was not accessed and the Titan neural model was not loaded.",
    )

    return RetentionScoreAssessment(
        assessment_id=assessment_id or f"retention_{uuid.uuid4().hex}",
        memory_id=source.memory_id,
        observed_at=source.observed_at or utc_now_iso(),
        retention_score=score,
        pressure_score=1.0 - score,
        rank=rank,
        recommended_action=action,
        protected=protected,
        protection_reasons=protection_reasons,
        reasons=reasons,
        risk_reasons=risk_reasons,
        explanation=explanation,
        components=components,
    )


def rank_hot_site_memories(
    memories: Iterable[RetentionScoringInput],
    *,
    weights: RetentionScoringWeights | None = None,
    thresholds: RetentionScoringThresholds | None = None,
    age_horizon_days: float = 365.0,
    usage_saturation_count: float = 20.0,
    observed_at: str | None = None,
    ranking_id: str | None = None,
) -> HotSiteRetentionRanking:
    """Rank memories by descending retention score with deterministic ties."""

    resolved_observed_at = observed_at or utc_now_iso()
    resolved_memories = tuple(memories)
    seen: set[str] = set()
    raw: list[RetentionScoreAssessment] = []

    for memory in resolved_memories:
        if memory.memory_id in seen:
            raise ValueError(f"Duplicate memory_id in retention ranking: {memory.memory_id}")
        seen.add(memory.memory_id)
        raw.append(
            assess_adaptive_retention(
                memory,
                weights=weights,
                thresholds=thresholds,
                age_horizon_days=age_horizon_days,
                usage_saturation_count=usage_saturation_count,
                assessment_id=f"retention_{memory.memory_id}",
            )
        )

    ordered = sorted(raw, key=lambda assessment: (-assessment.retention_score, assessment.memory_id))
    assessments = tuple(
        RetentionScoreAssessment(
            assessment_id=assessment.assessment_id,
            memory_id=assessment.memory_id,
            observed_at=resolved_observed_at,
            retention_score=assessment.retention_score,
            pressure_score=assessment.pressure_score,
            rank=index,
            recommended_action=assessment.recommended_action,
            protected=assessment.protected,
            protection_reasons=assessment.protection_reasons,
            reasons=assessment.reasons,
            risk_reasons=assessment.risk_reasons,
            explanation=assessment.explanation,
            components=assessment.components,
        )
        for index, assessment in enumerate(ordered, start=1)
    )
    scores = [assessment.retention_score for assessment in assessments]
    action_names = (
        "keep_protected",
        "keep_inactive",
        "keep",
        "watch",
        "review_for_soft_pruning",
        "deactivate_candidate",
    )
    action_counts = {
        action: sum(assessment.recommended_action == action for assessment in assessments)
        for action in action_names
    }

    return HotSiteRetentionRanking(
        ranking_id=ranking_id or f"retention_ranking_{uuid.uuid4().hex}",
        observed_at=resolved_observed_at,
        memory_count=len(assessments),
        mean_retention=fmean(scores) if scores else 0.0,
        maximum_retention=max(scores, default=0.0),
        minimum_retention=min(scores, default=0.0),
        protected_count=sum(assessment.protected for assessment in assessments),
        action_counts=action_counts,
        assessments=assessments,
    )
