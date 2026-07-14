from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    ControlledTopicRoutingService,
    TopicBlockRegistry,
    merge_topic_routing_metadata,
    route_validated_candidate,
    topic_routing_from_metadata,
)


class ControlledRoutingTests(unittest.TestCase):
    def test_routing_is_observation_only(self) -> None:
        routing = route_validated_candidate(
            candidate_id="candidate_test",
            content=(
                "Astronomy astronomy telescope stars"
            ),
            metadata={
                "tags": [
                    "space",
                    "astronomy",
                ]
            },
            importance=0.8,
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
            routing_id="routing_test",
        )

        self.assertTrue(
            routing.observation_only
        )
        self.assertFalse(
            routing.physical_partitioning
        )
        self.assertFalse(
            routing.retrieval_behavior_changed
        )
        self.assertEqual(
            routing.routing_id,
            "routing_test",
        )
        self.assertTrue(
            routing.block_id.startswith(
                "block_"
            )
        )

    def test_metadata_is_merged_non_destructively(
        self,
    ) -> None:
        routing = route_validated_candidate(
            candidate_id="candidate_test",
            content=(
                "guitar guitar melody concert"
            ),
            metadata={
                "subject": "Music preferences",
            },
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
            routing_id="routing_test",
        )

        original = {
            "subject": "Music preferences",
            "adaptive": {
                "other_metric": {
                    "value": 1,
                }
            },
        }

        merged = merge_topic_routing_metadata(
            original,
            routing,
        )

        self.assertEqual(
            merged["subject"],
            "Music preferences",
        )
        self.assertEqual(
            merged["adaptive"][
                "other_metric"
            ],
            {
                "value": 1,
            },
        )
        self.assertEqual(
            merged["adaptive"][
                "topic_block"
            ]["routing_id"],
            "routing_test",
        )
        self.assertNotIn(
            "topic_block",
            original["adaptive"],
        )

    def test_routing_can_be_read_from_metadata(
        self,
    ) -> None:
        routing = route_validated_candidate(
            candidate_id="candidate_test",
            content=(
                "database database indexing query"
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
            routing_id="routing_database",
        )

        metadata = merge_topic_routing_metadata(
            {},
            routing,
        )

        recovered = topic_routing_from_metadata(
            metadata
        )

        self.assertIsNotNone(recovered)
        self.assertEqual(
            recovered["routing_id"],
            "routing_database",
        )


class ControlledRoutingServiceTests(unittest.TestCase):
    def test_service_can_operate_without_registry(
        self,
    ) -> None:
        service = ControlledTopicRoutingService()

        routing, metadata = service.route(
            candidate_id="candidate_test",
            content=(
                "telescope stars astronomy"
            ),
            metadata={},
            importance=0.7,
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
            routing_id="routing_no_registry",
        )

        self.assertFalse(
            service.registry_enabled
        )
        self.assertEqual(
            metadata["adaptive"][
                "topic_block"
            ]["routing_id"],
            routing.routing_id,
        )

    def test_service_updates_optional_registry(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as root:
            registry = TopicBlockRegistry(
                Path(root)
                / "adaptive"
                / "topic_blocks.json"
            )

            service = ControlledTopicRoutingService(
                registry
            )

            routing, metadata = service.route(
                candidate_id="candidate_test",
                content=(
                    "astronomy astronomy telescope"
                ),
                metadata={
                    "tags": ["astronomy"],
                },
                importance=0.8,
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
                routing_id="routing_registry",
            )

            stored = registry.get(
                routing.block_id
            )

            self.assertTrue(
                service.registry_enabled
            )
            self.assertIsNotNone(stored)
            self.assertEqual(
                metadata["adaptive"][
                    "topic_block"
                ]["block_id"],
                routing.block_id,
            )


if __name__ == "__main__":
    unittest.main()
