"""Controlled topic-routing service.

The registry is optional. Memory validation remains the responsibility of the
existing validation service. This service only prepares metadata and, when a
registry is supplied, records an observation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memory.adaptive.block_registry import (
    TopicBlockRegistry,
)
from memory.adaptive.contracts import (
    ControlledTopicRouting,
    TopicBlockInput,
)
from memory.adaptive.routing import (
    merge_topic_routing_metadata,
    route_validated_candidate,
)
from memory.adaptive.topic_blocks import (
    observe_topic_block,
)


class ControlledTopicRoutingService:
    """Prepare logical topic metadata for validated candidates."""

    def __init__(
        self,
        registry: TopicBlockRegistry | None = None,
    ) -> None:
        self._registry = registry

    @property
    def registry_enabled(self) -> bool:
        return self._registry is not None

    def route(
        self,
        *,
        candidate_id: str,
        content: str,
        metadata: Mapping[str, Any] | None,
        importance: float,
        observed_at: str | None = None,
        routing_id: str | None = None,
    ) -> tuple[
        ControlledTopicRouting,
        dict[str, Any],
    ]:
        routing = route_validated_candidate(
            candidate_id=candidate_id,
            content=content,
            metadata=metadata,
            importance=importance,
            observed_at=observed_at,
            routing_id=routing_id,
        )

        enriched_metadata = (
            merge_topic_routing_metadata(
                metadata,
                routing,
            )
        )

        if self._registry is not None:
            observation = observe_topic_block(
                TopicBlockInput(
                    content=content,
                    item_id=candidate_id,
                    metadata_terms=(
                        routing.matched_terms
                    ),
                    importance=importance,
                    capacity=100,
                    used_items=1,
                    observed_at=(
                        routing.observed_at
                    ),
                ),
                routing_id=routing.routing_id,
            )

            self._registry.upsert_observation(
                observation
            )

        return routing, enriched_metadata
