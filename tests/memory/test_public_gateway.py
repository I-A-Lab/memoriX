from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import (
    CandidateStatus,
    ForgetAction,
    MemoryStoragePaths,
    RetrievalSource,
)
from memory.gateway import MemoriXGateway


class PublicGatewayTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.paths = (
            MemoryStoragePaths.from_runtime_root(
                self.temporary_directory.name
            )
        )

        torch.manual_seed(42)

        self.gateway = MemoriXGateway(
            storage_paths=self.paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def record_event(
        self,
        *,
        event_id: str = "event_gateway_001",
        content: str = (
            "Cold history stores every accepted event."
        ),
    ):
        return self.gateway.record_memory_event(
            event_id=event_id,
            content=content,
            event_type="architecture_rule",
            source="unit_test",
            project_id="memorix",
            session_id="session_gateway",
            importance=0.9,
            confidence=0.95,
            surprise=0.5,
            created_at="2026-07-13T18:00:00+00:00",
            archived_at="2026-07-13T18:01:00+00:00",
            metadata={"scope": "gateway"},
        )

    def create_validated_hot_memory(
        self,
        *,
        content: str = (
            "Active retrieval uses the Titan hot site only."
        ),
    ):
        candidate = (
            self.gateway.propose_memory_candidate(
                content=content,
                reason="Approved architectural contract.",
                source_event_ids=(
                    "event_gateway_candidate_001",
                ),
                importance=0.95,
                confidence=1.0,
                surprise=0.6,
                metadata={"scope": "retrieval"},
            )
        )

        return self.gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason=(
                "The architectural contract was approved."
            ),
        )


class GatewayRecordingTests(PublicGatewayTestCase):
    def test_record_writes_short_term_and_cold_directly(
        self,
    ) -> None:
        result = self.record_event()

        self.assertTrue(
            self.paths.short_term_events.is_file()
        )
        self.assertTrue(
            self.paths.cold_archive_events.is_file()
        )
        self.assertEqual(
            result.short_term_event.event_id,
            result.archived_event.event_id,
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["short_term_events"],
            1,
        )
        self.assertEqual(
            status["cold_archive_events"],
            1,
        )
        self.assertEqual(
            status["hot_memories_active"],
            0,
        )


class GatewayRetrievalContractTests(
    PublicGatewayTestCase
):
    def test_active_retrieval_prefers_hot_site(self) -> None:
        memory = self.create_validated_hot_memory()

        result = self.gateway.retrieve_memory(
            "Titan hot site active retrieval"
        )

        self.assertEqual(
            result.source,
            RetrievalSource.HOT_SITE,
        )
        self.assertGreaterEqual(
            len(result.matches),
            1,
        )
        self.assertEqual(
            result.matches[0].memory_id,
            memory.memory_id,
        )

    def test_retrieval_falls_back_to_short_term(self) -> None:
        recorded = self.record_event(
            content=(
                "The recent working token is "
                "STM-ONLY-7429."
            )
        )

        result = self.gateway.retrieve_memory(
            "STM-ONLY-7429"
        )

        self.assertEqual(
            result.source,
            RetrievalSource.SHORT_TERM,
        )
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(
            result.matches[0].memory_id,
            recorded.short_term_event.event_id,
        )
        self.assertEqual(
            result.matches[0].metadata["retrieval_tier"],
            "short_term",
        )
        self.assertFalse(
            result.matches[0].metadata["validated"]
        )

    def test_retrieval_falls_back_to_cold_after_stm_miss(
        self,
    ) -> None:
        recorded = self.record_event(
            content=(
                "The durable historical token is "
                "COLD-ONLY-7429."
            )
        )

        from memory.hot_site.short_term_memory import (
            ShortTermEventStore,
        )
        ShortTermEventStore(
            self.paths.short_term_events
        ).clear()

        result = self.gateway.retrieve_memory(
            "COLD-ONLY-7429"
        )

        self.assertEqual(
            result.source,
            RetrievalSource.COLD_SITE,
        )
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(
            result.matches[0].memory_id,
            recorded.archived_event.event_id,
        )
        self.assertEqual(
            result.matches[0].metadata["retrieval_tier"],
            "cold_site",
        )
        self.assertFalse(
            result.matches[0].metadata["validated"]
        )
        self.assertFalse(
            result.matches[0].metadata[
                "automatic_rehydration"
            ]
        )

    def test_short_term_wins_over_hot_site_and_cold(
        self,
    ) -> None:
        self.record_event(
            event_id="event_fallback_duplicate",
            content="Priority token is PRIORITY-9911.",
        )
        memory = self.create_validated_hot_memory(
            content=(
                "Validated priority token is PRIORITY-9911."
            ),
        )

        result = self.gateway.retrieve_memory(
            "PRIORITY-9911"
        )

        self.assertEqual(
            result.source,
            RetrievalSource.SHORT_TERM,
        )
        self.assertEqual(
            result.matches[0].memory_id,
            "event_fallback_duplicate",
        )
        self.assertEqual(
            result.matches[0].metadata["retrieval_tier"],
            "short_term",
        )
        self.assertFalse(
            result.matches[0].metadata["validated"]
        )

    def test_explicit_cold_search_finds_archived_event(
        self,
    ) -> None:
        recorded = self.record_event(
            content=(
                "The secret historical audit token is "
                "COLD-ONLY-7429."
            )
        )

        result = (
            self.gateway.search_cold_site_history(
                "COLD-ONLY-7429"
            )
        )

        self.assertEqual(
            result.source,
            RetrievalSource.COLD_AUDIT,
        )
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(
            result.matches[0].memory_id,
            recorded.short_term_event.event_id,
        )
        self.assertTrue(
            result.matches[0].metadata["audit_only"]
        )
        self.assertFalse(
            result.matches[0].metadata[
                "automatic_rehydration"
            ]
        )

    def test_cold_search_does_not_create_hot_memory(
        self,
    ) -> None:
        self.record_event(
            content="Audit-only historical information."
        )

        self.gateway.search_cold_site_history(
            "historical information"
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["hot_memories_total"],
            0,
        )
        self.assertFalse(
            self.paths.titan_neural_state.exists()
        )
        self.assertFalse(
            self.paths.titan_metadata.exists()
        )


class GatewayCandidateLifecycleTests(
    PublicGatewayTestCase
):
    def test_candidate_validation_is_hot_only(self) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "Validated candidates enter Titan only."
                ),
                reason="Stable architecture decision.",
                source_event_ids=(
                    "event_candidate_gateway_001",
                ),
                importance=0.9,
                confidence=0.95,
                surprise=0.5,
            )
        )

        memory = self.gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        stored_candidates = (
            self.gateway.list_memory_candidates()
        )

        self.assertEqual(
            stored_candidates[0].status,
            CandidateStatus.VALIDATED,
        )

        retrieval = self.gateway.retrieve_memory(
            "validated candidates Titan"
        )

        self.assertEqual(
            retrieval.source,
            RetrievalSource.HOT_SITE,
        )
        self.assertEqual(
            retrieval.matches[0].memory_id,
            memory.memory_id,
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_gateway_forget_is_hot_site_only(self) -> None:
        memory = self.create_validated_hot_memory()

        result = self.gateway.forget_memory(
            memory.memory_id,
            validated_by="human_reviewer",
            reason="Superseded active memory.",
        )

        self.assertEqual(
            result.action,
            ForgetAction.DEACTIVATED,
        )

        retrieval = self.gateway.retrieve_memory(
            "Titan hot site active retrieval"
        )

        self.assertEqual(retrieval.matches, ())
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )


class GatewayStatusTests(PublicGatewayTestCase):
    def test_status_exposes_hot_cold_contract(self) -> None:
        status = self.gateway.memory_status()

        self.assertEqual(
            status["retrieval_contract"],
            "short_term_then_hot_then_cold_fallback",
        )
        self.assertEqual(
            status["cold_site_contract"],
            "audit_search_plus_final_retrieval_fallback",
        )
        self.assertFalse(
            status["automatic_rehydration"]
        )


if __name__ == "__main__":
    unittest.main()
