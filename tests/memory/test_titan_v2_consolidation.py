from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from memory.cold_site.long_term_store import (
    ColdEventArchive,
)
from memory.consolidation import (
    ConsolidationAction,
    MemoryCandidateService,
    MemoryCandidateStore,
    TitanV2ConsolidationService,
    decide_event,
)
from memory.data import (
    CandidateStatus,
    MemoryStoragePaths,
    ShortTermEvent,
    ValidatedMemory,
)
from memory.gateway import MemoryEventService
from memory.hot_site.short_term_memory import (
    ShortTermEventStore,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)


class TitanV2ConsolidationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.paths = MemoryStoragePaths.from_runtime_root(
            self.temporary_directory.name
        )

        self.short_term_store = ShortTermEventStore(
            self.paths.short_term_events
        )
        self.cold_archive = ColdEventArchive(
            self.paths.cold_archive_events
        )
        self.event_service = MemoryEventService(
            self.short_term_store,
            self.cold_archive,
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

        self.consolidation = TitanV2ConsolidationService(
            self.short_term_store,
            self.candidate_store,
            self.candidate_service,
            self.hot_site,
        )

    @staticmethod
    def make_event(
        event_id: str,
        content: str,
        *,
        event_type: str = "architecture_rule",
        session_id: str | None = "session_v2",
        project_id: str | None = "memorix",
        importance: float = 0.9,
        confidence: float = 0.95,
        surprise: float = 0.4,
        metadata: dict | None = None,
    ) -> ShortTermEvent:
        return ShortTermEvent(
            event_id=event_id,
            content=content,
            event_type=event_type,
            source="unit_test",
            created_at="2026-07-13T17:00:00+00:00",
            session_id=session_id,
            project_id=project_id,
            importance=importance,
            confidence=confidence,
            surprise=surprise,
            metadata=metadata or {},
        )


class ConsolidationPolicyTests(
    TitanV2ConsolidationTestCase
):
    def test_high_importance_event_is_promoted(self) -> None:
        event = self.make_event(
            "event_policy_001",
            "Active retrieval uses only the Titan hot site.",
        )

        decision = decide_event(
            event,
            titan_surprise=0.2,
        )

        self.assertEqual(
            decision.action,
            ConsolidationAction.PROMOTE,
        )
        self.assertIsNotNone(
            decision.candidate_content
        )

    def test_low_confidence_event_is_skipped(self) -> None:
        event = self.make_event(
            "event_policy_002",
            "An unreliable statement.",
            confidence=0.2,
        )

        decision = decide_event(
            event,
            titan_surprise=0.9,
        )

        self.assertEqual(
            decision.action,
            ConsolidationAction.SKIP,
        )
        self.assertIn(
            "Confidence too low",
            decision.reason,
        )

    def test_excluded_event_type_is_skipped(self) -> None:
        event = self.make_event(
            "event_policy_003",
            "Raw diagnostic output.",
            event_type="debug_log",
        )

        decision = decide_event(
            event,
            titan_surprise=0.9,
        )

        self.assertEqual(
            decision.action,
            ConsolidationAction.SKIP,
        )


class TitanSurpriseTests(
    TitanV2ConsolidationTestCase
):
    def test_hot_site_computes_bounded_surprise(self) -> None:
        score = self.hot_site.compute_surprise(
            "A new architectural rule for memoriX."
        )

        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_scoring_uses_titan_surprise(self) -> None:
        event = self.make_event(
            "event_surprise_001",
            "A surprising memory architecture change.",
        )

        with patch.object(
            self.hot_site,
            "compute_surprise",
            return_value=0.87,
        ):
            scored = self.consolidation.score_events(
                (event,)
            )

        self.assertEqual(len(scored), 1)
        self.assertEqual(
            scored[0].decision.titan_surprise,
            0.87,
        )


class CandidateCreationTests(
    TitanV2ConsolidationTestCase
):
    def test_same_session_events_create_one_candidate(self) -> None:
        first = self.make_event(
            "event_group_001",
            "The cold site stores the complete history.",
        )
        second = self.make_event(
            "event_group_002",
            "Active retrieval never falls back to cold.",
        )

        self.event_service.record_event(first)
        self.event_service.record_event(second)

        report = self.consolidation.run()

        self.assertEqual(report.short_term_events, 2)
        self.assertEqual(report.groups_considered, 1)
        self.assertEqual(report.candidates_created, 1)

        candidates = (
            self.candidate_store.list_candidates()
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].status,
            CandidateStatus.PENDING,
        )
        self.assertEqual(
            set(candidates[0].source_event_ids),
            {
                first.event_id,
                second.event_id,
            },
        )

    def test_consolidation_does_not_validate_candidate(self) -> None:
        event = self.make_event(
            "event_candidate_001",
            "Candidates require human validation.",
        )

        self.event_service.record_event(event)

        report = self.consolidation.run()

        self.assertEqual(report.candidates_created, 1)
        self.assertEqual(
            self.hot_site.list_memories(),
            (),
        )
        self.assertFalse(
            self.paths.titan_neural_state.exists()
        )

    def test_duplicate_group_is_not_created_twice(self) -> None:
        event = self.make_event(
            "event_duplicate_001",
            "One event group creates one candidate.",
        )

        self.event_service.record_event(event)

        first_report = self.consolidation.run()
        second_report = self.consolidation.run()

        self.assertEqual(
            first_report.candidates_created,
            1,
        )
        self.assertEqual(
            second_report.candidates_created,
            0,
        )
        self.assertEqual(
            second_report.duplicate_groups_skipped,
            1,
        )
        self.assertEqual(
            len(
                self.candidate_store.list_candidates()
            ),
            1,
        )

    def test_low_value_event_creates_no_candidate(self) -> None:
        event = self.make_event(
            "event_low_001",
            "Minor informational note.",
            event_type="note",
            importance=0.1,
            confidence=0.9,
            surprise=0.0,
        )

        self.event_service.record_event(event)

        with patch.object(
            self.hot_site,
            "compute_surprise",
            return_value=0.0,
        ):
            report = self.consolidation.run()

        self.assertEqual(report.events_promoted, 0)
        self.assertEqual(report.candidates_created, 0)
        self.assertEqual(
            self.candidate_store.list_candidates(),
            (),
        )


class ColdSiteIsolationTests(
    TitanV2ConsolidationTestCase
):
    def test_consolidation_does_not_modify_cold_archive(self) -> None:
        event = self.make_event(
            "event_cold_001",
            "Cold history is excluded from consolidation.",
        )

        self.event_service.record_event(
            event,
            archived_at="2026-07-13T17:01:00+00:00",
        )

        cold_before = (
            self.paths.cold_archive_events.read_bytes()
        )

        self.consolidation.run()

        cold_after = (
            self.paths.cold_archive_events.read_bytes()
        )

        self.assertEqual(cold_after, cold_before)


class UpdateDetectionTests(
    TitanV2ConsolidationTestCase
):
    def store_active_memory(
        self,
        *,
        memory_id: str,
        content: str,
    ) -> ValidatedMemory:
        memory = ValidatedMemory(
            memory_id=memory_id,
            content=content,
            source_candidate_id="candidate_seed",
            created_at="2026-07-13T16:00:00+00:00",
            validated_at="2026-07-13T16:05:00+00:00",
            active=True,
        )

        self.hot_site.store_validated(
            memory,
            validated_by="unit_test",
            validation_reason="Seed active memory.",
        )

        return memory

    def test_update_candidate_targets_best_active_memory(
        self,
    ) -> None:
        existing = self.store_active_memory(
            memory_id="memory_color_old",
            content="The preferred color is blue.",
        )

        event = self.make_event(
            "event_update_001",
            (
                "Correction: replace the previous preferred "
                "color. The preferred color is now violet."
            ),
            metadata={
                "operation": "update",
            },
        )

        self.event_service.record_event(event)

        report = self.consolidation.run()
        candidate = (
            self.candidate_store.list_candidates()[0]
        )

        self.assertEqual(report.candidates_created, 1)
        self.assertTrue(
            candidate.metadata["update_candidate"]
        )
        self.assertTrue(
            candidate.metadata["update_target_found"]
        )
        self.assertEqual(
            candidate.target_memory_id,
            existing.memory_id,
        )

    def test_non_update_event_has_no_target_memory(self) -> None:
        self.store_active_memory(
            memory_id="memory_unrelated",
            content="The preferred color is blue.",
        )

        event = self.make_event(
            "event_normal_001",
            "The cold site is a durable event archive.",
        )

        self.event_service.record_event(event)

        self.consolidation.run()

        candidate = (
            self.candidate_store.list_candidates()[0]
        )

        self.assertFalse(
            candidate.metadata["update_candidate"]
        )
        self.assertIsNone(
            candidate.target_memory_id
        )


if __name__ == "__main__":
    unittest.main()
