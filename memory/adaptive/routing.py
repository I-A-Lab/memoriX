"""Controlled logical routing for human-validated memory candidates.

This module calculates topic-block metadata only. It performs no validation,
storage, physical partitioning, retrieval filtering, expansion, pruning,
cold fallback, or rehydration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from memory.adaptive.contracts import (
    ControlledTopicRouting,
    TopicBlockInput,
)
from memory.adaptive.topic_blocks import (
    observe_topic_block,
)


_TOPIC_METADATA_KEY = "adaptive"
_TOPIC_BLOCK_METADATA_KEY = "topic_block"


def _metadata_terms(
    metadata: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Extract explicit textual metadata without fixed domain knowledge."""

    if not metadata:
        return ()

    terms: list[str] = []

    for key in (
        "subject",
        "property",
        "tags",
        "terms",
        "topic_terms",
    ):
        value = metadata.get(key)

        if isinstance(value, str):
            if value.strip():
                terms.append(value)
            continue

        if isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            for item in value:
                if isinstance(item, str) and item.strip():
                    terms.append(item)

    return tuple(terms)


def route_validated_candidate(
    *,
    candidate_id: str,
    content: str,
    metadata: Mapping[str, Any] | None = None,
    importance: float = 0.5,
    observed_at: str | None = None,
    routing_id: str | None = None,
) -> ControlledTopicRouting:
    """Calculate logical block metadata for an explicitly validated candidate."""

    if not candidate_id.strip():
        raise ValueError(
            "candidate_id must be a non-empty string."
        )

    observation = observe_topic_block(
        TopicBlockInput(
            content=content,
            item_id=candidate_id,
            metadata_terms=_metadata_terms(metadata),
            importance=importance,
            capacity=100,
            used_items=1,
            observed_at=observed_at,
        ),
        routing_id=routing_id,
    )

    return ControlledTopicRouting(
        block_id=observation.block_id,
        label=observation.label,
        confidence=observation.routing.confidence,
        matched_terms=(
            observation.routing.matched_terms
        ),
        routing_id=observation.routing.routing_id,
        observed_at=observation.routing.observed_at,
    )


def merge_topic_routing_metadata(
    metadata: Mapping[str, Any] | None,
    routing: ControlledTopicRouting,
) -> dict[str, Any]:
    """Return copied metadata enriched with non-destructive topic routing."""

    merged = dict(metadata or {})

    adaptive_value = merged.get(
        _TOPIC_METADATA_KEY
    )

    adaptive = (
        dict(adaptive_value)
        if isinstance(adaptive_value, Mapping)
        else {}
    )

    adaptive[_TOPIC_BLOCK_METADATA_KEY] = (
        routing.to_dict()
    )

    merged[_TOPIC_METADATA_KEY] = adaptive

    return merged


def topic_routing_from_metadata(
    metadata: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    """Read topic routing metadata without using it for retrieval."""

    if not metadata:
        return None

    adaptive = metadata.get(
        _TOPIC_METADATA_KEY
    )

    if not isinstance(adaptive, Mapping):
        return None

    routing = adaptive.get(
        _TOPIC_BLOCK_METADATA_KEY
    )

    if not isinstance(routing, Mapping):
        return None

    return routing
