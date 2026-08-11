from __future__ import annotations

import gc
import json
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


class PythonMemoryEndToEndTestCase(unittest.TestCase):
    """Exercise the complete Python memory across gateway restarts."""

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
        self.gateway = self.make_gateway()

    def make_gateway(self) -> MemoriXGateway:
        """Create a gateway connected to the shared temporary runtime."""

        return MemoriXGateway(
            storage_paths=self.paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def restart_gateway(self) -> MemoriXGateway:
        """Simulate a new Python process using the same stored files."""

        gc.collect()
        torch.manual_seed(42)
        return self.make_gateway()

    def record_architecture_event(
        self,
        *,
        event_id: str,
        content: str,
        session_id: str = "session_end_to_end",
    ):
        """Record one high-value event through the public gateway."""

        return self.gateway.record_memory_event(
            event_id=event_id,
            content=content,
            event_type="architecture_rule",
            source="unit_test",
            project_id="memorix",
            session_id=session_id,
            importance=0.95,
            confidence=1.0,
            surprise=0.7,
            created_at="2026-07-13T21:00:00+00:00",
            archived_at="2026-07-13T21:01:00+00:00",
            metadata={
                "scope": "python_end_to_end",
            },
        )

    def create_validated_memory(
        self,
        *,
        content: str = (
            "Active retrieval uses only the Titan hot site."
        ),
    ):
        """Create and human-validate one explicit candidate."""

        candidate = (
            self.gateway.propose_memory_candidate(
                content=content,
                reason=(
                    "End-to-end validated memory test."
                ),
                source_event_ids=(
                    "event_end_to_end_seed",
                ),
                importance=0.95,
                confidence=1.0,
                surprise=0.6,
                metadata={
                    "scope": "python_end_to_end",
                },
            )
        )

        memory = (
            self.gateway.validate_memory_candidate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved during the end-to-end test."
                ),
            )
        )

        return candidate, memory


class FullPipelineRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_complete_pipeline_survives_restart(self) -> None:
        self.record_architecture_event(
            event_id="event_pipeline_001",
            content=(
                "Active retrieval is hot-site only and "
                "never falls back to cold history."
            ),
        )

        consolidation = (
            self.gateway.run_consolidation(
                mode="integration_test"
            )
        )

        self.assertEqual(
            consolidation.candidates_created,
            1,
        )

        pending_candidates = (
            self.gateway.list_memory_candidates(
                status=CandidateStatus.PENDING
            )
        )

        self.assertEqual(
            len(pending_candidates),
            1,
        )

        validated_memory = (
            self.gateway.validate_memory_candidate(
                pending_candidates[0].candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved complete-pipeline candidate."
                ),
            )
        )

        restarted = self.restart_gateway()

        status = restarted.memory_status()

        self.assertEqual(
            status["short_term_events"],
            1,
        )
        self.assertEqual(
            status["cold_archive_events"],
            1,
        )
        self.assertEqual(
            status["candidates"]["validated"],
            1,
        )
        self.assertEqual(
            status["hot_memories_active"],
            1,
        )

        retrieval = restarted.retrieve_memory(
            "hot-site retrieval without cold fallback"
        )

        self.assertEqual(
            retrieval.source,
            RetrievalSource.HOT_SITE,
        )
        self.assertGreaterEqual(
            len(retrieval.matches),
            1,
        )
        self.assertEqual(
            retrieval.matches[0].memory_id,
            validated_memory.memory_id,
        )


class DurableHistoryRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_short_term_and_cold_history_survive_restart(
        self,
    ) -> None:
        recorded = self.record_architecture_event(
            event_id="event_history_001",
            content=(
                "Cold history remains durable after a "
                "Python process restart."
            ),
        )

        restarted = self.restart_gateway()
        status = restarted.memory_status()

        self.assertEqual(
            status["short_term_events"],
            1,
        )
        self.assertEqual(
            status["cold_archive_events"],
            1,
        )

        cold_result = (
            restarted.search_cold_site_history(
                "durable after Python process restart"
            )
        )

        self.assertEqual(
            cold_result.source,
            RetrievalSource.COLD_AUDIT,
        )
        self.assertEqual(
            len(cold_result.matches),
            1,
        )
        self.assertEqual(
            cold_result.matches[0].memory_id,
            recorded.short_term_event.event_id,
        )

    def test_recent_information_falls_back_after_restart(
        self,
    ) -> None:
        recorded = self.record_architecture_event(
            event_id="event_cold_restart_001",
            content=(
                "Historical audit secret token "
                "COLD-RESTART-5517."
            ),
        )

        restarted = self.restart_gateway()

        recent_result = restarted.retrieve_memory(
            "COLD-RESTART-5517"
        )

        self.assertEqual(
            recent_result.source,
            RetrievalSource.SHORT_TERM,
        )
        self.assertEqual(
            recent_result.matches[0].memory_id,
            recorded.short_term_event.event_id,
        )

        from memory.hot_site.short_term_memory import (
            ShortTermEventStore,
        )
        ShortTermEventStore(
            self.paths.short_term_events
        ).clear()

        cold_result = restarted.retrieve_memory(
            "COLD-RESTART-5517"
        )

        self.assertEqual(
            cold_result.source,
            RetrievalSource.COLD_SITE,
        )
        self.assertEqual(
            cold_result.matches[0].memory_id,
            recorded.archived_event.event_id,
        )
        self.assertFalse(
            cold_result.matches[0].metadata["validated"]
        )

        audit_result = (
            restarted.search_cold_site_history(
                "COLD-RESTART-5517"
            )
        )

        self.assertEqual(
            audit_result.source,
            RetrievalSource.COLD_AUDIT,
        )
        self.assertEqual(
            len(audit_result.matches),
            1,
        )


class CandidateLifecycleRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_pending_candidate_survives_restart(
        self,
    ) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "A pending candidate must survive "
                    "a gateway restart."
                ),
                reason="Pending persistence test.",
                source_event_ids=(
                    "event_pending_restart_001",
                ),
                importance=0.8,
                confidence=0.9,
                surprise=0.4,
            )
        )

        restarted = self.restart_gateway()

        pending = restarted.list_memory_candidates(
            status=CandidateStatus.PENDING
        )

        self.assertEqual(len(pending), 1)
        self.assertEqual(
            pending[0].candidate_id,
            candidate.candidate_id,
        )

    def test_rejected_candidate_survives_restart(
        self,
    ) -> None:
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "This candidate will be rejected."
                ),
                reason="Rejection persistence test.",
                source_event_ids=(
                    "event_rejected_restart_001",
                ),
            )
        )

        self.gateway.reject_memory_candidate(
            candidate.candidate_id,
            rejected_by="human_reviewer",
            rejection_reason=(
                "The information is not durable."
            ),
        )

        restarted = self.restart_gateway()

        rejected = restarted.list_memory_candidates(
            status=CandidateStatus.REJECTED
        )

        self.assertEqual(len(rejected), 1)
        self.assertEqual(
            rejected[0].candidate_id,
            candidate.candidate_id,
        )
        self.assertEqual(
            restarted.memory_status()[
                "hot_memories_total"
            ],
            0,
        )


class HotSiteRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_soft_forget_survives_restart(self) -> None:
        _, memory = self.create_validated_memory()

        forget_result = self.gateway.forget_memory(
            memory.memory_id,
            validated_by="human_reviewer",
            reason=(
                "Deactivate before restart."
            ),
        )

        self.assertEqual(
            forget_result.action,
            ForgetAction.DEACTIVATED,
        )

        restarted = self.restart_gateway()
        status = restarted.memory_status()

        self.assertEqual(
            status["hot_memories_total"],
            1,
        )
        self.assertEqual(
            status["hot_memories_active"],
            0,
        )

        retrieval = restarted.retrieve_memory(
            "active retrieval Titan hot site"
        )

        self.assertEqual(
            retrieval.source,
            RetrievalSource.COLD_SITE,
        )
        self.assertEqual(
            retrieval.matches,
            (),
        )


class NightlyRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_nightly_state_and_log_survive_restart(
        self,
    ) -> None:
        self.record_architecture_event(
            event_id="event_nightly_restart_001",
            content=(
                "Nightly consolidation must preserve "
                "cold history across restarts."
            ),
        )

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertEqual(
            report.short_term_events_cleared,
            1,
        )
        self.assertFalse(
            report.cold_site_modified
        )
        self.assertFalse(
            report.automatic_candidate_validation
        )

        restarted = self.restart_gateway()
        status = restarted.memory_status()

        self.assertEqual(
            status["short_term_events"],
            0,
        )
        self.assertEqual(
            status["cold_archive_events"],
            1,
        )
        self.assertEqual(
            status["candidates"]["pending"],
            1,
        )
        self.assertEqual(
            status["hot_memories_active"],
            0,
        )

        lines = self.paths.nightly_logs.read_text(
            encoding="utf-8"
        ).splitlines()

        self.assertEqual(len(lines), 1)

        payload = json.loads(lines[0])

        self.assertEqual(
            payload["nightly_scope"],
            "short_term_to_hot_site_only",
        )
        self.assertFalse(
            payload["cold_site_modified"]
        )
        self.assertFalse(
            payload[
                "automatic_candidate_validation"
            ]
        )


class ConsolidationRestartTests(
    PythonMemoryEndToEndTestCase
):
    def test_duplicate_candidate_prevention_survives_restart(
        self,
    ) -> None:
        self.record_architecture_event(
            event_id="event_duplicate_restart_001",
            content=(
                "The same short-term group must not "
                "create duplicate candidates."
            ),
        )

        first_report = self.gateway.run_consolidation(
            mode="before_restart"
        )

        self.assertEqual(
            first_report.candidates_created,
            1,
        )

        restarted = self.restart_gateway()

        second_report = restarted.run_consolidation(
            mode="after_restart"
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
                restarted.list_memory_candidates()
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
