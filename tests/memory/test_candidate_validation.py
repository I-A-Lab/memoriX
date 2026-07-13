from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from memory.consolidation import (
    CandidateAlreadyProcessedError,
    MemoryCandidateService,
    MemoryCandidateStore,
)
from memory.data import (
    CandidateStatus,
    MemoryStoragePaths,
)
from memory.gateway import (
    CandidateValidationError,
    MemoryValidationService,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)


class CandidateValidationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.paths = MemoryStoragePaths.from_runtime_root(
            self.temporary_directory.name
        )

        self.candidate_store = MemoryCandidateStore(
            self.paths.memory_candidates
        )
        self.candidate_service = MemoryCandidateService(
            self.candidate_store
        )

        torch.manual_seed(42)

        self.hot_site = HotSiteTitanMemory(
            neural_state_path=self.paths.titan_neural_state,
            metadata_path=self.paths.titan_metadata,
            d_model=32,
            hidden_dim=32,
            max_items=100,
            device="cpu",
            top_k=5,
            min_score=0.0,
        )

        self.validation_service = MemoryValidationService(
            self.candidate_store,
            self.hot_site,
        )

    def propose_candidate(
        self,
        *,
        content: str = "Active retrieval uses the hot site only.",
        target_memory_id: str | None = None,
    ):
        return self.candidate_service.propose(
            content=content,
            reason="Repeated architecture decision.",
            source_event_ids=(
                "event_candidate_001",
                "event_candidate_002",
            ),
            importance=0.9,
            confidence=0.95,
            surprise=0.6,
            target_memory_id=target_memory_id,
            metadata={"scope": "retrieval"},
        )


class CandidateStoreTests(CandidateValidationTestCase):
    def test_candidate_is_persisted_as_pending(self) -> None:
        candidate = self.propose_candidate()

        stored = self.candidate_store.get(
            candidate.candidate_id
        )

        self.assertEqual(
            stored.status,
            CandidateStatus.PENDING,
        )
        self.assertEqual(
            self.candidate_store.list_candidates(
                status=CandidateStatus.PENDING
            ),
            (stored,),
        )


class CandidateValidationTests(CandidateValidationTestCase):
    def test_validation_stores_memory_in_hot_site_only(self) -> None:
        candidate = self.propose_candidate()

        memory = self.validation_service.validate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved architecture.",
        )

        stored_candidate = self.candidate_store.get(
            candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.VALIDATED,
        )
        self.assertEqual(
            stored_candidate.metadata[
                "validated_memory_id"
            ],
            memory.memory_id,
        )

        hot_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(len(hot_memories), 1)
        self.assertEqual(
            hot_memories[0].memory_id,
            memory.memory_id,
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_validated_candidate_cannot_be_validated_twice(self) -> None:
        candidate = self.propose_candidate()

        self.validation_service.validate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        with self.assertRaises(
            CandidateAlreadyProcessedError
        ):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason="Second approval.",
            )

    def test_rejection_does_not_write_to_titan(self) -> None:
        candidate = self.propose_candidate()

        rejected = self.validation_service.reject(
            candidate.candidate_id,
            rejected_by="human_reviewer",
            rejection_reason="Not durable enough.",
        )

        self.assertEqual(
            rejected.status,
            CandidateStatus.REJECTED,
        )
        self.assertEqual(
            self.hot_site.list_memories(),
            (),
        )
        self.assertFalse(
            self.paths.titan_neural_state.exists()
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_rejected_candidate_cannot_be_validated(self) -> None:
        candidate = self.propose_candidate()

        self.validation_service.reject(
            candidate.candidate_id,
            rejected_by="human_reviewer",
            rejection_reason="Rejected.",
        )

        with self.assertRaises(
            CandidateAlreadyProcessedError
        ):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason="Late approval.",
            )


class CandidateUpdateTests(CandidateValidationTestCase):
    def test_validated_update_replaces_old_hot_memory(self) -> None:
        original_candidate = self.propose_candidate(
            content="The preferred color is blue."
        )

        original_memory = self.validation_service.validate(
            original_candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Initial fact approved.",
        )

        update_candidate = self.propose_candidate(
            content="The preferred color is violet.",
            target_memory_id=original_memory.memory_id,
        )

        updated_memory = self.validation_service.validate(
            update_candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved correction.",
        )

        self.assertEqual(
            updated_memory.supersedes_memory_id,
            original_memory.memory_id,
        )
        self.assertEqual(updated_memory.version, 2)

        all_memories = {
            memory.memory_id: memory
            for memory in self.hot_site.list_memories()
        }

        self.assertFalse(
            all_memories[original_memory.memory_id].active
        )
        self.assertTrue(
            all_memories[updated_memory.memory_id].active
        )

        active_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(len(active_memories), 1)
        self.assertEqual(
            active_memories[0].memory_id,
            updated_memory.memory_id,
        )

        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_update_rejects_unknown_target_memory(self) -> None:
        candidate = self.propose_candidate(
            target_memory_id="memory_unknown"
        )

        with self.assertRaises(
            CandidateValidationError
        ):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason="Invalid update target.",
            )

        stored_candidate = self.candidate_store.get(
            candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )


if __name__ == "__main__":
    unittest.main()
