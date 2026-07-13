from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from memory.data import (
    ForgetAction,
    RetrievalSource,
    ValidatedMemory,
)
from memory.hot_site.titan_active_memory import (
    HotSiteInputError,
    HotSiteTitanMemory,
)


class TitanHotSiteTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        root = Path(self.temporary_directory.name)

        self.neural_path = root / "hot_site" / "titan_memory.pt"
        self.metadata_path = (
            root
            / "hot_site"
            / "titan_metadata.jsonl"
        )
        self.cold_path = (
            root
            / "cold_site"
            / "events_archive.jsonl"
        )

        torch.manual_seed(42)

        self.hot_site = HotSiteTitanMemory(
            neural_state_path=self.neural_path,
            metadata_path=self.metadata_path,
            d_model=32,
            hidden_dim=32,
            max_items=100,
            device="cpu",
            top_k=5,
            min_score=0.0,
        )

    @staticmethod
    def make_memory(
        memory_id: str = "memory_titan_001",
        content: str = (
            "Active retrieval must use the Titan hot site only."
        ),
    ) -> ValidatedMemory:
        return ValidatedMemory(
            memory_id=memory_id,
            content=content,
            source_candidate_id="candidate_titan_001",
            created_at="2026-07-13T16:00:00+00:00",
            validated_at="2026-07-13T16:05:00+00:00",
            active=True,
            version=1,
            metadata={
                "source_agent": "unit_test",
                "roles": ["developer"],
            },
        )


class TitanImportTests(TitanHotSiteTestCase):
    def test_backend_uses_real_titan_model(self) -> None:
        backend_name = type(
            self.hot_site._backend.memory
        ).__name__

        self.assertEqual(
            backend_name,
            "TitanExternalMemory",
        )


class TitanStorageTests(TitanHotSiteTestCase):
    def test_validated_memory_is_stored_in_titan(self) -> None:
        memory = self.make_memory()

        returned = self.hot_site.store_validated(
            memory,
            validated_by="human_reviewer",
            validation_reason="Architecture approved.",
        )

        self.assertEqual(returned, memory)
        self.assertTrue(self.neural_path.is_file())
        self.assertTrue(self.metadata_path.is_file())

        listed = self.hot_site.list_memories()

        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].memory_id, memory.memory_id)
        self.assertTrue(listed[0].active)

    def test_inactive_memory_is_rejected(self) -> None:
        memory = self.make_memory()
        memory.active = False

        with self.assertRaises(HotSiteInputError):
            self.hot_site.store_validated(
                memory,
                validated_by="human_reviewer",
            )

    def test_reviewer_is_required(self) -> None:
        with self.assertRaises(HotSiteInputError):
            self.hot_site.store_validated(
                self.make_memory(),
                validated_by="   ",
            )


class TitanRetrievalTests(TitanHotSiteTestCase):
    def test_retrieval_is_explicitly_hot_site_only(self) -> None:
        memory = self.make_memory()

        self.hot_site.store_validated(
            memory,
            validated_by="human_reviewer",
        )

        result = self.hot_site.retrieve(
            "Titan hot site active retrieval",
            role="developer",
        )

        self.assertEqual(
            result.source,
            RetrievalSource.HOT_SITE,
        )
        self.assertGreaterEqual(len(result.matches), 1)
        self.assertEqual(
            result.matches[0].memory_id,
            memory.memory_id,
        )

    def test_retrieval_does_not_create_or_read_cold_storage(self) -> None:
        self.hot_site.store_validated(
            self.make_memory(),
            validated_by="human_reviewer",
        )

        self.hot_site.retrieve("active retrieval")

        self.assertFalse(self.cold_path.exists())


class TitanForgetTests(TitanHotSiteTestCase):
    def test_soft_forget_deactivates_hot_memory(self) -> None:
        memory = self.make_memory()

        self.hot_site.store_validated(
            memory,
            validated_by="human_reviewer",
        )

        result = self.hot_site.soft_forget(
            memory.memory_id,
            validated_by="human_reviewer",
            reason="Superseded by an approved update.",
        )

        self.assertEqual(
            result.action,
            ForgetAction.DEACTIVATED,
        )

        active_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(active_memories, ())

        retrieval = self.hot_site.retrieve(
            "Titan hot site active retrieval"
        )

        self.assertEqual(retrieval.matches, ())
        self.assertFalse(self.cold_path.exists())

    def test_unknown_memory_returns_not_found(self) -> None:
        result = self.hot_site.soft_forget(
            "memory_unknown",
            validated_by="human_reviewer",
            reason="Test unknown memory.",
        )

        self.assertEqual(
            result.action,
            ForgetAction.NOT_FOUND,
        )


class TitanStatsTests(TitanHotSiteTestCase):
    def test_stats_identify_neural_backend(self) -> None:
        stats = self.hot_site.stats()

        self.assertEqual(
            stats["backend"],
            "titan_external",
        )


if __name__ == "__main__":
    unittest.main()
