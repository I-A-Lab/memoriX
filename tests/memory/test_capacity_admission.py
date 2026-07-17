from __future__ import annotations

import tempfile
import unittest

import torch

from memory.consolidation import MemoryCandidateService, MemoryCandidateStore
from memory.data import CandidateStatus, MemoryStoragePaths
from memory.gateway import CapacityAdmissionError, MemoryValidationService
from memory.hot_site.titan_active_memory import HotSiteTitanMemory


class CapacityAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.paths = MemoryStoragePaths.from_runtime_root(temporary.name)
        self.store = MemoryCandidateStore(self.paths.memory_candidates)
        self.candidates = MemoryCandidateService(self.store)
        torch.manual_seed(42)
        self.hot_site = HotSiteTitanMemory(
            neural_state_path=self.paths.titan_neural_state,
            metadata_path=self.paths.titan_metadata,
            d_model=32,
            hidden_dim=32,
            max_items=10,
            device="cpu",
            top_k=5,
            min_score=0.0,
        )
        self.validation = MemoryValidationService(
            self.store,
            self.hot_site,
            configured_capacity=1,
        )

    def propose(self, content: str):
        return self.candidates.propose(
            content=content,
            reason="Capacity admission test.",
            source_event_ids=("event_capacity",),
            importance=0.5,
            confidence=0.8,
            surprise=0.2,
        )

    def test_first_candidate_is_admitted(self) -> None:
        candidate = self.propose("First durable fact.")
        self.validation.validate(
            candidate.candidate_id,
            validated_by="reviewer",
            validation_reason="Approved.",
        )
        self.assertEqual(len(self.hot_site.list_memories(active_only=True)), 1)

    def test_full_hot_site_rejects_before_mutation(self) -> None:
        first = self.propose("First durable fact.")
        self.validation.validate(
            first.candidate_id,
            validated_by="reviewer",
            validation_reason="Approved.",
        )
        second = self.propose("Second durable fact.")
        neural_before = self.paths.titan_neural_state.read_bytes()
        metadata_before = self.paths.titan_metadata.read_bytes()

        with self.assertRaises(CapacityAdmissionError):
            self.validation.validate(
                second.candidate_id,
                validated_by="reviewer",
                validation_reason="Would exceed capacity.",
            )

        stored = self.store.get(second.candidate_id)
        self.assertEqual(stored.status, CandidateStatus.PENDING)
        self.assertEqual(self.paths.titan_neural_state.read_bytes(), neural_before)
        self.assertEqual(self.paths.titan_metadata.read_bytes(), metadata_before)
        self.assertFalse(self.paths.cold_archive_events.exists())
