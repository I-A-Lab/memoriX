from __future__ import annotations

import tempfile
import unittest

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway


class ValidationTopicRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.gateway = MemoriXGateway(
            storage_paths=(
                MemoryStoragePaths.from_runtime_root(
                    self.temporary_directory.name
                )
            ),
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def test_human_validation_adds_topic_metadata(
        self,
    ) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "Astronomy telescope stars "
                    "and astronomy research."
                ),
                reason=(
                    "Controlled routing test."
                ),
                source_event_ids=(
                    "event_topic_routing",
                ),
                importance=0.9,
                confidence=1.0,
                surprise=0.5,
                metadata={
                    "subject": (
                        "Astronomy research"
                    ),
                    "tags": [
                        "space",
                        "astronomy",
                    ],
                },
            )
        )

        memory = (
            self.gateway.validate_memory_candidate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved controlled-routing test."
                ),
            )
        )

        adaptive = memory.metadata.get(
            "adaptive"
        )

        self.assertIsInstance(
            adaptive,
            dict,
        )

        topic_block = adaptive.get(
            "topic_block"
        )

        self.assertIsInstance(
            topic_block,
            dict,
        )
        self.assertTrue(
            topic_block["block_id"].startswith(
                "block_"
            )
        )
        self.assertTrue(
            topic_block["observation_only"]
        )
        self.assertFalse(
            topic_block["physical_partitioning"]
        )
        self.assertFalse(
            topic_block[
                "retrieval_behavior_changed"
            ]
        )

    def test_pending_candidate_is_not_modified(
        self,
    ) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "Guitar melody concert."
                ),
                reason=(
                    "Pending-candidate isolation test."
                ),
                source_event_ids=(
                    "event_pending_routing",
                ),
                metadata={
                    "subject": "Music",
                },
            )
        )

        self.assertNotIn(
            "adaptive",
            candidate.metadata,
        )

    def test_retrieval_remains_hot_only(
        self,
    ) -> None:
        event = self.gateway.record_memory_event(
            content=(
                "Cold-only routing token "
                "ROUTING-COLD-7712."
            ),
            event_type="routing_test",
            source="test",
        )

        result = self.gateway.retrieve_memory(
            "ROUTING-COLD-7712"
        )

        self.assertEqual(
            result.source,
            "short_term",
        )
        self.assertGreaterEqual(
            len(result.matches),
            1,
        )

        cold = (
            self.gateway.search_cold_site_history(
                "ROUTING-COLD-7712"
            )
        )

        self.assertEqual(
            cold.source,
            "cold_audit",
        )
        self.assertGreaterEqual(
            len(cold.matches),
            1,
        )

        self.assertIsNotNone(event)


if __name__ == "__main__":
    unittest.main()
