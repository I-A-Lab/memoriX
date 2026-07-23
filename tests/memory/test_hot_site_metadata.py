from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway


class HotSiteMetadataPreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        paths = MemoryStoragePaths.from_runtime_root(
            self.temporary_directory.name
        )

        torch.manual_seed(42)

        self.gateway = MemoriXGateway(
            storage_paths=paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def test_candidate_metadata_survives_hot_retrieval(
        self,
    ) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "Subject: Facade retrieval contract\n"
                    "Content: memory_retrieve is hot-only.\n"
                    "Tags: architecture, hot-only"
                ),
                reason=(
                    "Metadata preservation regression test."
                ),
                source_event_ids=(
                    "event_metadata_preservation",
                ),
                importance=0.95,
                confidence=1.0,
                surprise=0.5,
                metadata={
                    "subject": (
                        "Facade retrieval contract"
                    ),
                    "original_content": (
                        "memory_retrieve is hot-only."
                    ),
                    "tags": [
                        "architecture",
                        "hot-only",
                    ],
                },
            )
        )

        memory = (
            self.gateway.validate_memory_candidate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved metadata regression test."
                ),
            )
        )

        result = self.gateway.retrieve_memory(
            "Facade retrieval contract hot-only"
        )

        matching = [
            match
            for match in result.matches
            if match.memory_id == memory.memory_id
        ]

        self.assertEqual(
            len(matching),
            1,
        )

        for match in matching:
            metadata = match.metadata

            self.assertEqual(
                metadata["subject"],
                "Facade retrieval contract",
            )
            self.assertEqual(
                metadata["original_content"],
                "memory_retrieve is hot-only.",
            )
            self.assertEqual(
                metadata["tags"],
                [
                    "architecture",
                    "hot-only",
                ],
            )


if __name__ == "__main__":
    unittest.main()
