from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

import torch

from memory.data import (
    CandidateStatus,
    MemoryStoragePaths,
)
from memory.gateway import MemoriXGateway
from memory.sync import (
    COLD_SITE_CONTRACT,
    NIGHTLY_SCOPE,
    ColdSiteModifiedError,
    snapshot_file,
)


class NightlyConsolidationTestCase(unittest.TestCase):
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

    def record_promotable_event(
        self,
        *,
        event_id: str = "event_nightly_001",
    ):
        return self.gateway.record_memory_event(
            event_id=event_id,
            content=(
                "Active retrieval is hot-site only and "
                "cold history is audit-only."
            ),
            event_type="architecture_rule",
            source="unit_test",
            project_id="memorix",
            session_id="session_nightly",
            importance=0.95,
            confidence=1.0,
            surprise=0.7,
            created_at="2026-07-13T20:00:00+00:00",
            archived_at="2026-07-13T20:01:00+00:00",
        )

    def create_validated_memory(self):
        candidate = (
            self.gateway.propose_memory_candidate(
                content=(
                    "Validated memories are replayed in "
                    "the Titan hot site."
                ),
                reason="Nightly replay test.",
                source_event_ids=(
                    "event_replay_seed",
                ),
                importance=0.9,
                confidence=1.0,
                surprise=0.5,
            )
        )

        return self.gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved replay seed.",
        )


class NightlyContractTests(
    NightlyConsolidationTestCase
):
    def test_nightly_creates_pending_candidate_only(
        self,
    ) -> None:
        self.record_promotable_event()

        report = (
            self.gateway.run_nightly_consolidation()
        )

        candidates = (
            self.gateway.list_memory_candidates()
        )

        self.assertEqual(
            report.consolidation.candidates_created,
            1,
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0].status,
            CandidateStatus.PENDING,
        )
        self.assertFalse(
            report.automatic_candidate_validation
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["hot_memories_total"],
            0,
        )

    def test_nightly_preserves_cold_site_exactly(
        self,
    ) -> None:
        self.record_promotable_event()

        cold_before = snapshot_file(
            self.paths.cold_archive_events
        )

        report = (
            self.gateway.run_nightly_consolidation()
        )

        cold_after = snapshot_file(
            self.paths.cold_archive_events
        )

        self.assertEqual(cold_after, cold_before)
        self.assertFalse(
            report.cold_site_modified
        )
        self.assertEqual(
            report.cold_before,
            report.cold_after,
        )
        self.assertEqual(
            report.cold_site_contract,
            COLD_SITE_CONTRACT,
        )

    def test_nightly_scope_is_hot_path_only(self) -> None:
        self.record_promotable_event()

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertEqual(
            report.nightly_scope,
            NIGHTLY_SCOPE,
        )
        self.assertEqual(
            report.nightly_scope,
            "short_term_to_hot_site_only",
        )


class NightlyCleanupTests(
    NightlyConsolidationTestCase
):
    def test_short_term_is_cleared_after_success(
        self,
    ) -> None:
        self.record_promotable_event()

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertEqual(
            report.short_term_events_cleared,
            1,
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["short_term_events"],
            0,
        )
        self.assertEqual(
            status["cold_archive_events"],
            1,
        )

    def test_short_term_can_be_preserved(self) -> None:
        self.record_promotable_event()

        report = (
            self.gateway.run_nightly_consolidation(
                clear_short_term_after_success=False
            )
        )

        self.assertEqual(
            report.short_term_events_cleared,
            0,
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["short_term_events"],
            1,
        )


class NightlyReplayTests(
    NightlyConsolidationTestCase
):
    def test_active_hot_memory_is_replayed(self) -> None:
        memory = self.create_validated_memory()

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertEqual(
            report.active_memories_replayed,
            1,
        )

        retrieval = self.gateway.retrieve_memory(
            "validated memories replayed Titan hot site"
        )

        self.assertGreaterEqual(
            len(retrieval.matches),
            1,
        )
        self.assertEqual(
            retrieval.matches[0].memory_id,
            memory.memory_id,
        )

    def test_inactive_memory_is_not_replayed(self) -> None:
        memory = self.create_validated_memory()

        self.gateway.forget_memory(
            memory.memory_id,
            validated_by="human_reviewer",
            reason="Deactivate before nightly replay.",
        )

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertEqual(
            report.active_memories_replayed,
            0,
        )


class NightlyLogTests(
    NightlyConsolidationTestCase
):
    def test_successful_run_writes_json_log(self) -> None:
        self.record_promotable_event()

        report = (
            self.gateway.run_nightly_consolidation()
        )

        self.assertTrue(
            self.paths.nightly_logs.is_file()
        )

        lines = self.paths.nightly_logs.read_text(
            encoding="utf-8"
        ).splitlines()

        self.assertEqual(len(lines), 1)

        payload = json.loads(lines[0])

        self.assertEqual(
            payload["nightly_scope"],
            NIGHTLY_SCOPE,
        )
        self.assertEqual(
            payload["cold_site_contract"],
            COLD_SITE_CONTRACT,
        )
        self.assertFalse(
            payload["cold_site_modified"]
        )
        self.assertFalse(
            payload[
                "automatic_candidate_validation"
            ]
        )
        self.assertEqual(
            payload["completed_at"],
            report.completed_at,
        )


class NightlyProtectionTests(
    NightlyConsolidationTestCase
):
    def test_detects_unexpected_cold_modification(
        self,
    ) -> None:
        self.record_promotable_event()

        original_run = (
            self.gateway._consolidation_service.run
        )

        def malicious_run(*, mode: str):
            report = original_run(mode=mode)

            with self.paths.cold_archive_events.open(
                "a",
                encoding="utf-8",
            ) as stream:
                stream.write(
                    '{"unexpected":"mutation"}\n'
                )

            return report

        with patch.object(
            self.gateway._consolidation_service,
            "run",
            side_effect=malicious_run,
        ):
            with self.assertRaises(
                ColdSiteModifiedError
            ):
                self.gateway.run_nightly_consolidation()

        self.assertFalse(
            self.paths.nightly_logs.exists()
        )


if __name__ == "__main__":
    unittest.main()
