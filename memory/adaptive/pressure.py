"""Pure and observable memory-pressure calculations.

This module does not know about the cold site, Titan persistence, candidates,
expansion, pruning, or OpenCode. It transforms explicit measurements into one
immutable observation.
"""

from __future__ import annotations

import math
import uuid
from statistics import fmean
from typing import Mapping, Sequence

from memory.adaptive.contracts import (
    PressureComponents,
    PressureLevel,
    PressureObservation,
    PressureObservationInput,
    PressureThresholds,
    PressureWeights,
    utc_now_iso,
)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def calculate_usage_ratio(
    used_items: int,
    capacity: int,
) -> float:
    """Return used/capacity normalized to [0, 1]."""

    if used_items < 0:
        raise ValueError(
            "used_items must be non-negative."
        )

    if capacity <= 0:
        raise ValueError(
            "capacity must be strictly positive."
        )

    return _clamp_unit(used_items / capacity)


def calculate_momentum(
    usage_samples: Sequence[int],
    capacity: int,
) -> float:
    """Measure sustained positive growth across a usage window.

    Each positive delta is normalized by capacity. Negative deltas do not
    produce negative pressure. A single sample has zero momentum.
    """

    if capacity <= 0:
        raise ValueError(
            "capacity must be strictly positive."
        )

    if any(sample < 0 for sample in usage_samples):
        raise ValueError(
            "usage samples must be non-negative."
        )

    if len(usage_samples) < 2:
        return 0.0

    positive_deltas = [
        max(0, current - previous)
        for previous, current in zip(
            usage_samples,
            usage_samples[1:],
        )
    ]

    return _clamp_unit(
        fmean(positive_deltas) / capacity
    )


def calculate_entropy(
    term_frequencies: Mapping[str, int] | None,
) -> float:
    """Return normalized Shannon entropy for observed terms.

    Zero or one active term has zero entropy. The result is normalized by the
    theoretical maximum entropy for the active vocabulary.
    """

    if not term_frequencies:
        return 0.0

    if any(
        count < 0
        for count in term_frequencies.values()
    ):
        raise ValueError(
            "term frequencies must be non-negative."
        )

    positive_counts = [
        count
        for count in term_frequencies.values()
        if count > 0
    ]

    if len(positive_counts) <= 1:
        return 0.0

    total = sum(positive_counts)

    probabilities = [
        count / total
        for count in positive_counts
    ]

    raw_entropy = -sum(
        probability
        * math.log2(probability)
        for probability in probabilities
    )

    maximum_entropy = math.log2(
        len(positive_counts)
    )

    if maximum_entropy == 0.0:
        return 0.0

    return _clamp_unit(
        raw_entropy / maximum_entropy
    )


def calculate_surprise(
    surprise_samples: Sequence[float],
) -> float:
    """Return mean normalized surprise for an observation window."""

    if not surprise_samples:
        return 0.0

    if any(
        value < 0.0 or value > 1.0
        for value in surprise_samples
    ):
        raise ValueError(
            "surprise samples must be between 0 and 1."
        )

    return _clamp_unit(
        fmean(surprise_samples)
    )


def calculate_pressure_persistence(
    previous_pressure_samples: Sequence[float],
    threshold: float,
) -> float:
    """Return the fraction of prior pressure samples above a threshold."""

    if threshold < 0.0 or threshold > 1.0:
        raise ValueError(
            "persistence threshold must be between 0 and 1."
        )

    if not previous_pressure_samples:
        return 0.0

    if any(
        value < 0.0 or value > 1.0
        for value in previous_pressure_samples
    ):
        raise ValueError(
            "pressure samples must be between 0 and 1."
        )

    persistent_count = sum(
        value >= threshold
        for value in previous_pressure_samples
    )

    return _clamp_unit(
        persistent_count
        / len(previous_pressure_samples)
    )


def calculate_memory_pressure(
    components: PressureComponents,
    weights: PressureWeights | None = None,
) -> float:
    """Combine normalized components into one pressure score."""

    resolved_weights = weights or PressureWeights()
    resolved_weights.validate()

    weighted_sum = (
        components.usage_ratio
        * resolved_weights.usage_ratio
        + components.momentum
        * resolved_weights.momentum
        + components.entropy
        * resolved_weights.entropy
        + components.surprise
        * resolved_weights.surprise
        + components.persistence
        * resolved_weights.persistence
    )

    total_weight = (
        resolved_weights.usage_ratio
        + resolved_weights.momentum
        + resolved_weights.entropy
        + resolved_weights.surprise
        + resolved_weights.persistence
    )

    return _clamp_unit(
        weighted_sum / total_weight
    )


def classify_pressure_level(
    pressure: float,
    thresholds: PressureThresholds | None = None,
) -> PressureLevel:
    """Label pressure without recommending or performing an action."""

    resolved_thresholds = (
        thresholds or PressureThresholds()
    )
    resolved_thresholds.validate()

    normalized = _clamp_unit(pressure)

    if normalized >= resolved_thresholds.critical:
        return PressureLevel.CRITICAL

    if normalized >= resolved_thresholds.high:
        return PressureLevel.HIGH

    if normalized >= resolved_thresholds.watch:
        return PressureLevel.WATCH

    return PressureLevel.STABLE


def _build_explanation(
    components: PressureComponents,
    level: PressureLevel,
) -> tuple[str, ...]:
    ordered = sorted(
        components.as_dict().items(),
        key=lambda item: item[1],
        reverse=True,
    )

    strongest_name, strongest_value = ordered[0]

    return (
        (
            f"Observed pressure level is {level.value}; "
            "this is descriptive only."
        ),
        (
            f"Strongest normalized component is "
            f"{strongest_name}={strongest_value:.4f}."
        ),
        (
            "No expansion, pruning, validation, retrieval fallback, "
            "or rehydration action was requested."
        ),
    )


def observe_memory_pressure(
    source: PressureObservationInput,
    *,
    weights: PressureWeights | None = None,
    thresholds: PressureThresholds | None = None,
    observation_id: str | None = None,
) -> PressureObservation:
    """Calculate one immutable pressure observation."""

    source.validate()

    resolved_thresholds = (
        thresholds or PressureThresholds()
    )
    resolved_thresholds.validate()

    components = PressureComponents(
        usage_ratio=calculate_usage_ratio(
            source.used_items,
            source.capacity,
        ),
        momentum=calculate_momentum(
            source.usage_samples,
            source.capacity,
        ),
        entropy=calculate_entropy(
            source.term_frequencies,
        ),
        surprise=calculate_surprise(
            source.surprise_samples,
        ),
        persistence=calculate_pressure_persistence(
            source.previous_pressure_samples,
            resolved_thresholds.persistence,
        ),
    )

    pressure = calculate_memory_pressure(
        components,
        weights,
    )

    level = classify_pressure_level(
        pressure,
        resolved_thresholds,
    )

    return PressureObservation(
        observation_id=(
            observation_id
            or f"pressure_{uuid.uuid4().hex}"
        ),
        scope_id=source.scope_id,
        observed_at=(
            source.observed_at
            or utc_now_iso()
        ),
        level=level,
        memory_pressure=pressure,
        components=components,
        used_items=source.used_items,
        capacity=source.capacity,
        sample_sizes={
            "usage": len(source.usage_samples),
            "terms": len(
                source.term_frequencies or {}
            ),
            "surprise": len(
                source.surprise_samples
            ),
            "previous_pressure": len(
                source.previous_pressure_samples
            ),
        },
        explanation=_build_explanation(
            components,
            level,
        ),
    )
