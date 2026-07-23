"""Controlled adaptive decoration for validated memory metadata.

The existing validation service remains responsible for human validation and
hot-site insertion. This module only prepares topic-block metadata before
that insertion.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from memory.adaptive.routing_service import (
    ControlledTopicRoutingService,
)


class AdaptiveValidationMetadataService:
    """Enrich candidate metadata before explicit human validation."""

    def __init__(
        self,
        routing_service: (
            ControlledTopicRoutingService | None
        ) = None,
    ) -> None:
        self._routing_service = (
            routing_service
            or ControlledTopicRoutingService()
        )

    def enrich(
        self,
        *,
        candidate_id: str,
        content: str,
        metadata: Mapping[str, Any] | None,
        importance: float,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        _, enriched_metadata = (
            self._routing_service.route(
                candidate_id=candidate_id,
                content=content,
                metadata=metadata,
                importance=importance,
                observed_at=observed_at,
            )
        )

        return enriched_metadata
