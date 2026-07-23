from __future__ import annotations

import json
import unittest

from memory.data import (
    ArchivedEvent,
    CandidateStatus,
    ForgetAction,
    ForgetResult,
    MemoryCandidate,
    RetrievalResult,
    RetrievalSource,
    RetrievedMemory,
    ShortTermEvent,
    ValidatedMemory,
)


class ShortTermEventTests(unittest.TestCase):
    def test_event_round_trip_is_json_compatible(self) -> None:
        event = ShortTermEvent(
            event_id="event_test_001",
            content="The retrieval contract is hot-site only.",
            event_type="architecture_decision",
            source="unit_test",
            created_at="2026-07-13T10:00:00+00:00",
            project_id="memorix",
            session_id="session_test",
            importance=0.9,
            confidence=1.0,
            surprise=0.7,
            metadata={
                "language": "en",
                "tags": ["retrieval", "hot_site"],
            },
        )

        serialized = event.to_dict()
        json.dumps(serialized)

        restored = ShortTermEvent.from_dict(serialized)

        self.assertEqual(restored, event)
        self.assertIsNot(restored.metadata, event.metadata)

    def test_event_rejects_empty_content(self) -> None:
        with self.assertRaises(ValueError):
            ShortTermEvent(
                content="   ",
                event_type="note",
                source="unit_test",
            )

    def test_event_rejects_invalid_score(self) -> None:
        with self.assertRaises(ValueError):
            ShortTermEvent(
                content="A valid event.",
                event_type="note",
                source="unit_test",
                importance=1.5,
            )

    def test_event_requires_timezone_aware_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            ShortTermEvent(
                content="A valid event.",
                event_type="note",
                source="unit_test",
                created_at="2026-07-13T10:00:00",
            )


class ArchivedEventTests(unittest.TestCase):
    def test_archive_is_created_from_short_term_event(self) -> None:
        event = ShortTermEvent(
            event_id="event_archive_001",
            content="Cold storage keeps the complete durable history.",
            event_type="architecture_decision",
            source="unit_test",
            created_at="2026-07-13T10:00:00+00:00",
            project_id="memorix",
            session_id="session_archive",
            metadata={"scope": "cold_site"},
        )

        archive = ArchivedEvent.from_short_term_event(
            event,
            archived_at="2026-07-13T10:05:00+00:00",
        )

        self.assertEqual(archive.event_id, event.event_id)
        self.assertEqual(
            archive.original_created_at,
            event.created_at,
        )
        self.assertEqual(
            archive.archived_at,
            "2026-07-13T10:05:00+00:00",
        )
        self.assertEqual(archive.metadata, event.metadata)
        self.assertIsNot(archive.metadata, event.metadata)

        serialized = archive.to_dict()
        json.dumps(serialized)

        self.assertEqual(
            ArchivedEvent.from_dict(serialized),
            archive,
        )


class MemoryCandidateTests(unittest.TestCase):
    def test_candidate_defaults_to_pending(self) -> None:
        candidate = MemoryCandidate(
            candidate_id="candidate_test_001",
            content="Use hot-site retrieval only.",
            reason="Repeated architectural decision.",
            source_event_ids=(
                "event_test_001",
                "event_test_002",
            ),
            created_at="2026-07-13T11:00:00+00:00",
            importance=0.8,
            confidence=0.9,
            surprise=0.6,
        )

        self.assertEqual(
            candidate.status,
            CandidateStatus.PENDING,
        )

        serialized = candidate.to_dict()
        json.dumps(serialized)

        restored = MemoryCandidate.from_dict(serialized)

        self.assertEqual(restored, candidate)
        self.assertIsInstance(
            restored.source_event_ids,
            tuple,
        )

    def test_candidate_requires_source_events(self) -> None:
        with self.assertRaises(ValueError):
            MemoryCandidate(
                content="A candidate without a source.",
                reason="Invalid test candidate.",
                source_event_ids=(),
            )


class ValidatedMemoryTests(unittest.TestCase):
    def test_validated_memory_round_trip(self) -> None:
        memory = ValidatedMemory(
            memory_id="memory_test_001",
            content="Validated memories belong to the hot site.",
            source_candidate_id="candidate_test_001",
            created_at="2026-07-13T12:00:00+00:00",
            validated_at="2026-07-13T12:05:00+00:00",
            active=True,
            version=2,
            supersedes_memory_id="memory_test_000",
            metadata={"reviewer": "human"},
        )

        serialized = memory.to_dict()
        json.dumps(serialized)

        self.assertEqual(
            ValidatedMemory.from_dict(serialized),
            memory,
        )

    def test_validated_memory_rejects_invalid_version(self) -> None:
        with self.assertRaises(ValueError):
            ValidatedMemory(
                content="Invalid memory version.",
                source_candidate_id="candidate_test",
                version=0,
            )


class RetrievalContractTests(unittest.TestCase):
    def test_hot_site_retrieval_result_round_trip(self) -> None:
        match = RetrievedMemory(
            memory_id="memory_test_001",
            content="Active retrieval is hot-site only.",
            score=0.96,
            metadata={"active": True},
        )

        result = RetrievalResult(
            query="Where does active retrieval search?",
            source=RetrievalSource.HOT_SITE,
            matches=(match,),
            retrieved_at="2026-07-13T13:00:00+00:00",
        )

        serialized = result.to_dict()
        json.dumps(serialized)

        restored = RetrievalResult.from_dict(serialized)

        self.assertEqual(restored, result)
        self.assertEqual(
            restored.source,
            RetrievalSource.HOT_SITE,
        )

    def test_cold_audit_source_is_explicit(self) -> None:
        result = RetrievalResult(
            query="Show historical events.",
            source=RetrievalSource.COLD_AUDIT,
            matches=(),
        )

        self.assertEqual(
            result.source,
            RetrievalSource.COLD_AUDIT,
        )


class ForgetContractTests(unittest.TestCase):
    def test_forget_result_round_trip(self) -> None:
        result = ForgetResult(
            memory_id="memory_test_001",
            action=ForgetAction.DEACTIVATED,
            reason="Superseded by a validated update.",
            changed_at="2026-07-13T14:00:00+00:00",
        )

        serialized = result.to_dict()
        json.dumps(serialized)

        self.assertEqual(
            ForgetResult.from_dict(serialized),
            result,
        )


class IdentifierTests(unittest.TestCase):
    def test_default_identifiers_have_expected_prefixes(self) -> None:
        event = ShortTermEvent(
            content="Automatic event identifier.",
            event_type="note",
            source="unit_test",
        )

        candidate = MemoryCandidate(
            content="Automatic candidate identifier.",
            reason="Identifier test.",
            source_event_ids=(event.event_id,),
        )

        memory = ValidatedMemory(
            content="Automatic memory identifier.",
            source_candidate_id=candidate.candidate_id,
        )

        self.assertTrue(event.event_id.startswith("event_"))
        self.assertTrue(
            candidate.candidate_id.startswith("candidate_")
        )
        self.assertTrue(memory.memory_id.startswith("memory_"))


if __name__ == "__main__":
    unittest.main()
