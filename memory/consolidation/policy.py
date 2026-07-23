"""Selection policy used by Titan V2 consolidation.

The policy classifies short-term events. It does not create candidates,
validate memories, write into Titan, or modify the cold site.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re

from memory.data import ShortTermEvent


class ConsolidationAction(str, Enum):
    """Possible decisions for one short-term event."""

    PROMOTE = "promote"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class ConsolidationPolicy:
    """Thresholds controlling short-term event promotion."""

    min_importance: float = 0.60
    min_surprise: float = 0.65
    min_confidence: float = 0.50
    min_combined_score: float = 0.70

    always_promote_event_types: tuple[str, ...] = (
        "validated_decision",
        "validated_project",
        "architecture_rule",
        "memory_policy",
        "test_result",
        "bug_fixed",
    )

    excluded_event_types: tuple[str, ...] = (
        "raw_log",
        "debug_log",
        "temporary_thought",
        "draft",
        "rejected_project",
        "command",
    )

    weak_keywords: tuple[str, ...] = (
        "temporary",
        "draft",
        "ignore this",
        "not important",
        "just a log",
        "debug only",
        "random test",
    )


@dataclass(frozen=True, slots=True)
class ConsolidationDecision:
    """Decision produced for one short-term event."""

    event_id: str
    action: ConsolidationAction
    reason: str
    candidate_content: str | None
    importance: float
    confidence: float
    original_surprise: float
    titan_surprise: float
    effective_surprise: float
    combined_score: float


def clamp_unit(value: float) -> float:
    """Clamp one finite numeric value to [0, 1]."""

    numeric = float(value)

    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0

    return min(1.0, max(0.0, numeric))


def normalize_content(content: str) -> str:
    """Normalize text for duplicate detection."""

    normalized = content.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(
        r"[^a-z0-9àâçéèêëîïôûùüÿñæœ _'-]",
        "",
        normalized,
    )
    return normalized


def compute_combined_score(
    event: ShortTermEvent,
    *,
    titan_surprise: float,
) -> float:
    """Combine importance, surprise, and confidence.

    This preserves the weighting used in the historical memoriX
    consolidation policy:

    - importance: 50%;
    - surprise: 30%;
    - confidence: 20%.

    Validated inputs and successful test results receive bounded bonuses.
    """

    effective_surprise = max(
        clamp_unit(event.surprise),
        clamp_unit(titan_surprise),
    )

    score = (
        0.50 * clamp_unit(event.importance)
        + 0.30 * effective_surprise
        + 0.20 * clamp_unit(event.confidence)
    )

    if event.metadata.get("validated") is True:
        score += 0.15

    if event.metadata.get("test_passed") is True:
        score += 0.10

    return clamp_unit(score)


def build_candidate_content(event: ShortTermEvent) -> str:
    """Build the candidate text for one promoted event."""

    content = event.content.strip()

    prefixes = {
        "validated_project": "Validated project memory",
        "architecture_rule": "Architecture rule",
        "memory_policy": "Memory policy",
        "test_result": "Test result",
        "bug_fixed": "Bug fixed",
    }

    prefix = prefixes.get(event.event_type)

    if prefix is None:
        return content

    return f"{prefix}: {content}"


def decide_event(
    event: ShortTermEvent,
    *,
    titan_surprise: float,
    policy: ConsolidationPolicy | None = None,
) -> ConsolidationDecision:
    """Decide whether one short-term event should be promoted."""

    if not isinstance(event, ShortTermEvent):
        raise TypeError("event must be a ShortTermEvent.")

    selected_policy = policy or ConsolidationPolicy()

    effective_surprise = max(
        clamp_unit(event.surprise),
        clamp_unit(titan_surprise),
    )

    combined_score = compute_combined_score(
        event,
        titan_surprise=titan_surprise,
    )

    if event.event_type in selected_policy.excluded_event_types:
        return ConsolidationDecision(
            event_id=event.event_id,
            action=ConsolidationAction.SKIP,
            reason=(
                f"Excluded event type: {event.event_type}"
            ),
            candidate_content=None,
            importance=event.importance,
            confidence=event.confidence,
            original_surprise=event.surprise,
            titan_surprise=clamp_unit(titan_surprise),
            effective_surprise=effective_surprise,
            combined_score=combined_score,
        )

    lowered_content = event.content.lower()

    if any(
        keyword in lowered_content
        for keyword in selected_policy.weak_keywords
    ):
        return ConsolidationDecision(
            event_id=event.event_id,
            action=ConsolidationAction.SKIP,
            reason="Weak or temporary content.",
            candidate_content=None,
            importance=event.importance,
            confidence=event.confidence,
            original_surprise=event.surprise,
            titan_surprise=clamp_unit(titan_surprise),
            effective_surprise=effective_surprise,
            combined_score=combined_score,
        )

    if event.confidence < selected_policy.min_confidence:
        return ConsolidationDecision(
            event_id=event.event_id,
            action=ConsolidationAction.SKIP,
            reason=(
                "Confidence too low: "
                f"{event.confidence:.2f} < "
                f"{selected_policy.min_confidence:.2f}"
            ),
            candidate_content=None,
            importance=event.importance,
            confidence=event.confidence,
            original_surprise=event.surprise,
            titan_surprise=clamp_unit(titan_surprise),
            effective_surprise=effective_surprise,
            combined_score=combined_score,
        )

    should_promote = (
        event.event_type
        in selected_policy.always_promote_event_types
        or event.importance
        >= selected_policy.min_importance
        or effective_surprise
        >= selected_policy.min_surprise
        or combined_score
        >= selected_policy.min_combined_score
    )

    if should_promote:
        return ConsolidationDecision(
            event_id=event.event_id,
            action=ConsolidationAction.PROMOTE,
            reason=(
                "Promoted by Titan V2 policy "
                f"(score={combined_score:.2f}, "
                f"importance={event.importance:.2f}, "
                f"surprise={effective_surprise:.2f}, "
                f"confidence={event.confidence:.2f})."
            ),
            candidate_content=build_candidate_content(event),
            importance=event.importance,
            confidence=event.confidence,
            original_surprise=event.surprise,
            titan_surprise=clamp_unit(titan_surprise),
            effective_surprise=effective_surprise,
            combined_score=combined_score,
        )

    return ConsolidationDecision(
        event_id=event.event_id,
        action=ConsolidationAction.SKIP,
        reason=(
            "Below consolidation thresholds "
            f"(score={combined_score:.2f})."
        ),
        candidate_content=None,
        importance=event.importance,
        confidence=event.confidence,
        original_surprise=event.surprise,
        titan_surprise=clamp_unit(titan_surprise),
        effective_surprise=effective_surprise,
        combined_score=combined_score,
    )
