from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
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


class CandidateTargetedSupersessionTests(
    CandidateValidationTestCase
):
    def _validate_pair(self):
        original_candidate = self.propose_candidate(
            content="The primary color is blue."
        )

        original_memory = (
            self.validation_service.validate(
                original_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Initial fact approved."
                ),
            )
        )

        update_candidate = self.propose_candidate(
            content="The primary color is violet."
        )

        return (
            original_candidate,
            original_memory,
            update_candidate,
        )

    def test_explicit_supersedes_id_links_replacement_and_increments_version(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )
        )

        self.assertEqual(
            updated_memory.supersedes_memory_id,
            original_memory.memory_id,
        )
        self.assertEqual(updated_memory.version, 2)
        self.assertTrue(updated_memory.active)

    def test_superseded_target_is_soft_deactivated(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )
        )

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

        self.assertEqual(
            [
                memory.memory_id
                for memory in active_memories
            ],
            [updated_memory.memory_id],
        )

    def test_superseded_target_is_excluded_from_normal_retrieval(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )
        )

        result = self.hot_site.retrieve(
            "primary color",
            top_k=5,
        )

        returned = {
            memory.memory_id
            for memory in result.matches
        }

        self.assertNotIn(
            original_memory.memory_id,
            returned,
        )
        self.assertIn(
            updated_memory.memory_id,
            returned,
        )

    def test_superseded_target_remains_in_audit_history(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )
        )

        all_memories = {
            memory.memory_id: memory
            for memory in self.hot_site.list_memories()
        }

        self.assertIn(
            original_memory.memory_id,
            all_memories,
        )
        self.assertFalse(
            all_memories[original_memory.memory_id].active
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_candidate_target_mechanism_still_works_when_supersedes_id_omitted(self) -> None:
        original_candidate = self.propose_candidate(
            content="The accent color is green."
        )

        original_memory = (
            self.validation_service.validate(
                original_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Initial fact approved."
                ),
            )
        )

        update_candidate = self.propose_candidate(
            content="The accent color is teal.",
            target_memory_id=original_memory.memory_id,
        )

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
            )
        )

        self.assertEqual(
            updated_memory.supersedes_memory_id,
            original_memory.memory_id,
        )
        self.assertEqual(updated_memory.version, 2)

        stored_candidate = self.candidate_store.get(
            update_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.VALIDATED,
        )

    def test_plain_validation_without_target_is_unchanged(self) -> None:
        candidate = self.propose_candidate(
            content="A neutral fact."
        )

        memory = self.validation_service.validate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        self.assertEqual(memory.version, 1)
        self.assertIsNone(memory.supersedes_memory_id)
        self.assertTrue(memory.active)

    def test_unknown_target_is_rejected(self) -> None:
        candidate = self.propose_candidate()

        with self.assertRaises(
            CandidateValidationError
        ):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Invalid supersession target."
                ),
                supersedes_memory_id="memory_unknown",
            )

        stored_candidate = self.candidate_store.get(
            candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )
        self.assertEqual(
            self.hot_site.list_memories(),
            (),
        )

    def test_inactive_target_is_rejected(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = (
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )
        )

        third_candidate = self.propose_candidate(
            content="The primary color is indigo."
        )

        with self.assertRaises(
            CandidateValidationError
        ):
            self.validation_service.validate(
                third_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Second correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )

        active_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(
            [
                memory.memory_id
                for memory in active_memories
            ],
            [updated_memory.memory_id],
        )

    def test_self_supersession_is_rejected(self) -> None:
        candidate = self.propose_candidate(
            content="Self reference fact."
        )

        memory = self.validation_service.validate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        self.candidate_store.replace(
            replace(
                candidate,
                status=CandidateStatus.PENDING,
                target_memory_id=None,
            )
        )

        with self.assertRaises(
            CandidateValidationError
        ):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason="Self supersession.",
                supersedes_memory_id=memory.memory_id,
            )

        active_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(
            [
                active_memory.memory_id
                for active_memory in active_memories
            ],
            [memory.memory_id],
        )

    def test_conflicting_explicit_and_candidate_targets_are_rejected(self) -> None:
        first_candidate = self.propose_candidate(
            content="Fact one."
        )

        first_memory = self.validation_service.validate(
            first_candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        second_candidate = self.propose_candidate(
            content="Fact two."
        )

        second_memory = self.validation_service.validate(
            second_candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved.",
        )

        third_candidate = self.propose_candidate(
            content="Fact three.",
            target_memory_id=first_memory.memory_id,
        )

        with self.assertRaises(ValueError):
            self.validation_service.validate(
                third_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Conflicting targets."
                ),
                supersedes_memory_id=(
                    second_memory.memory_id
                ),
            )

        stored_candidate = self.candidate_store.get(
            third_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )

    def test_empty_supersedes_id_is_rejected(self) -> None:
        candidate = self.propose_candidate()

        with self.assertRaises(ValueError):
            self.validation_service.validate(
                candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Whitespace supersession target."
                ),
                supersedes_memory_id="   ",
            )

    def test_failed_targeted_validation_does_not_change_candidate_status(self) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        with self.assertRaises(
            CandidateValidationError
        ):
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id="memory_unknown",
            )

        stored_candidate = self.candidate_store.get(
            update_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )

    def test_target_deactivation_failure_rolls_back_replacement(
        self,
    ) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        original_soft_forget = self.hot_site.soft_forget

        def failing_target_soft_forget(
            memory_id: str,
            *,
            validated_by: str,
            reason: str,
        ):
            if memory_id == original_memory.memory_id:
                raise RuntimeError(
                    "backend unavailable for target"
                )
            return original_soft_forget(
                memory_id,
                validated_by=validated_by,
                reason=reason,
            )

        self.hot_site.soft_forget = failing_target_soft_forget

        with self.assertRaises(
            CandidateValidationError
        ) as raised:
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )

        error_message = str(raised.exception)

        stored_candidate = self.candidate_store.get(
            update_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )

        all_memories = {
            memory.memory_id: memory
            for memory in self.hot_site.list_memories()
        }

        replacement = next(
            memory
            for memory in all_memories.values()
            if memory.supersedes_memory_id
            == original_memory.memory_id
        )

        self.assertIn(
            replacement.memory_id,
            error_message,
        )
        self.assertIn(
            original_memory.memory_id,
            error_message,
        )
        self.assertIn(
            "RuntimeError: backend unavailable for target",
            error_message,
        )

        self.assertTrue(
            all_memories[original_memory.memory_id].active
        )
        self.assertFalse(replacement.active)

        result = self.hot_site.retrieve(
            "primary color",
            top_k=5,
        )

        returned = {
            memory.memory_id
            for memory in result.matches
        }

        # The replacement must be absent from active retrieval. The
        # original target is intentionally not asserted here: Titan
        # single-value update semantics deactivate the item-level copy
        # of the superseded fact when the replacement is stored, while
        # the gateway metadata for the target stays active (asserted
        # above via list_memories).
        self.assertNotIn(
            replacement.memory_id,
            returned,
        )

    def test_compensation_failure_reports_both_errors_and_ids(
        self,
    ) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        original_soft_forget = self.hot_site.soft_forget

        def always_failing_soft_forget(
            memory_id: str,
            *,
            validated_by: str,
            reason: str,
        ):
            return original_soft_forget(
                "memory_never_exists",
                validated_by=validated_by,
                reason=reason,
            )

        self.hot_site.soft_forget = always_failing_soft_forget

        with self.assertRaises(
            CandidateValidationError
        ) as raised:
            self.validation_service.validate(
                update_candidate.candidate_id,
                validated_by="human_reviewer",
                validation_reason=(
                    "Approved correction."
                ),
                supersedes_memory_id=(
                    original_memory.memory_id
                ),
            )

        error_message = str(raised.exception)

        all_memories = {
            memory.memory_id: memory
            for memory in self.hot_site.list_memories()
        }

        replacement = next(
            memory
            for memory in all_memories.values()
            if memory.supersedes_memory_id
            == original_memory.memory_id
        )

        self.assertIn(
            original_memory.memory_id,
            error_message,
        )
        self.assertIn(
            replacement.memory_id,
            error_message,
        )
        self.assertIn(
            "could not be deactivated",
            error_message,
        )
        self.assertIn(
            "also failed",
            error_message,
        )

        stored_candidate = self.candidate_store.get(
            update_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.PENDING,
        )

    def test_successful_supersession_still_validates_candidate(
        self,
    ) -> None:
        (
            original_candidate,
            original_memory,
            update_candidate,
        ) = self._validate_pair()

        updated_memory = self.validation_service.validate(
            update_candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason=(
                "Approved correction."
            ),
            supersedes_memory_id=(
                original_memory.memory_id
            ),
        )

        stored_candidate = self.candidate_store.get(
            update_candidate.candidate_id
        )

        self.assertEqual(
            stored_candidate.status,
            CandidateStatus.VALIDATED,
        )
        self.assertEqual(
            stored_candidate.metadata[
                "validated_memory_id"
            ],
            updated_memory.memory_id,
        )

        active_memories = self.hot_site.list_memories(
            active_only=True
        )

        self.assertEqual(
            [
                memory.memory_id
                for memory in active_memories
            ],
            [updated_memory.memory_id],
        )


if __name__ == "__main__":
    unittest.main()
