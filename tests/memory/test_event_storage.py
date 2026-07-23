from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory.cold_site.long_term_store import ColdEventArchive
from memory.data import (
    ArchivedEvent,
    JsonlDecodeError,
    MemoryStoragePaths,
    ShortTermEvent,
)
from memory.gateway import (
    DuplicateEventError,
    MemoryEventConsistencyError,
    MemoryEventService,
)
from memory.hot_site.short_term_memory import ShortTermEventStore


class EventStorageTestCase(unittest.TestCase):
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
        self.service = MemoryEventService(
            self.short_term_store,
            self.cold_archive,
        )

    @staticmethod
    def make_event(
        event_id: str = "event_storage_001",
    ) -> ShortTermEvent:
        return ShortTermEvent(
            event_id=event_id,
            content="Short-term events are archived directly.",
            event_type="architecture_decision",
            source="unit_test",
            created_at="2026-07-13T15:00:00+00:00",
            project_id="memorix",
            session_id="session_storage",
            importance=0.9,
            confidence=1.0,
            surprise=0.7,
            metadata={
                "tags": ["short_term", "cold_site"],
                "language": "en",
            },
        )


class MemoryStoragePathsTests(EventStorageTestCase):
    def test_paths_use_distinct_short_and_cold_locations(self) -> None:
        self.assertNotEqual(
            self.paths.short_term_events,
            self.paths.cold_archive_events,
        )
        self.assertEqual(
            self.paths.short_term_events.name,
            "events.jsonl",
        )
        self.assertEqual(
            self.paths.cold_archive_events.name,
            "events_archive.jsonl",
        )


class ShortTermEventStoreTests(EventStorageTestCase):
    def test_missing_store_is_empty(self) -> None:
        self.assertEqual(
            self.short_term_store.list_events(),
            (),
        )

    def test_append_and_load_event(self) -> None:
        event = self.make_event()

        returned = self.short_term_store.append(event)

        self.assertEqual(returned, event)
        self.assertTrue(self.short_term_store.path.is_file())
        self.assertEqual(
            self.short_term_store.list_events(),
            (event,),
        )
        self.assertEqual(
            self.short_term_store.get_by_id(event.event_id),
            event,
        )

    def test_clear_only_affects_short_term_storage(self) -> None:
        first = self.make_event("event_clear_001")
        second = self.make_event("event_clear_002")

        self.short_term_store.append(first)
        self.short_term_store.append(second)

        removed = self.short_term_store.clear()

        self.assertEqual(removed, 2)
        self.assertEqual(
            self.short_term_store.list_events(),
            (),
        )


class ColdEventArchiveTests(EventStorageTestCase):
    def test_archive_preserves_original_event_identity(self) -> None:
        event = self.make_event()

        archived = self.cold_archive.archive(
            event,
            archived_at="2026-07-13T15:05:00+00:00",
        )

        self.assertIsInstance(archived, ArchivedEvent)
        self.assertEqual(archived.event_id, event.event_id)
        self.assertEqual(
            archived.original_created_at,
            event.created_at,
        )
        self.assertEqual(
            archived.archived_at,
            "2026-07-13T15:05:00+00:00",
        )
        self.assertEqual(
            self.cold_archive.list_events(),
            (archived,),
        )

    def test_archive_file_contains_one_json_object_per_line(self) -> None:
        first = self.make_event("event_archive_001")
        second = self.make_event("event_archive_002")

        self.cold_archive.archive(first)
        self.cold_archive.archive(second)

        lines = self.cold_archive.path.read_text(
            encoding="utf-8"
        ).splitlines()

        self.assertEqual(len(lines), 2)

        decoded = [json.loads(line) for line in lines]

        self.assertEqual(
            [item["event_id"] for item in decoded],
            [first.event_id, second.event_id],
        )


class MemoryEventServiceTests(EventStorageTestCase):
    def test_record_event_writes_short_term_and_cold_directly(self) -> None:
        event = self.make_event()

        result = self.service.record_event(
            event,
            archived_at="2026-07-13T15:05:00+00:00",
        )

        self.assertEqual(result.short_term_event, event)
        self.assertEqual(
            result.archived_event.event_id,
            event.event_id,
        )
        self.assertEqual(
            self.short_term_store.list_events(),
            (event,),
        )
        self.assertEqual(
            len(self.cold_archive.list_events()),
            1,
        )

    def test_duplicate_event_is_rejected_before_new_writes(self) -> None:
        event = self.make_event()

        self.service.record_event(event)

        with self.assertRaises(DuplicateEventError):
            self.service.record_event(event)

        self.assertEqual(
            len(self.short_term_store.list_events()),
            1,
        )
        self.assertEqual(
            len(self.cold_archive.list_events()),
            1,
        )

    def test_inconsistent_existing_state_is_detected(self) -> None:
        event = self.make_event()

        self.short_term_store.append(event)

        with self.assertRaises(MemoryEventConsistencyError):
            self.service.record_event(event)

        self.assertEqual(
            self.cold_archive.list_events(),
            (),
        )

    def test_cold_failure_is_reported_as_consistency_error(self) -> None:
        event = self.make_event()

        with patch.object(
            self.cold_archive,
            "archive",
            side_effect=OSError("simulated cold failure"),
        ):
            with self.assertRaises(MemoryEventConsistencyError):
                self.service.record_event(event)

        self.assertEqual(
            self.short_term_store.list_events(),
            (event,),
        )
        self.assertEqual(
            self.cold_archive.list_events(),
            (),
        )


class JsonlIntegrityTests(EventStorageTestCase):
    def test_invalid_json_is_not_silently_ignored(self) -> None:
        self.paths.short_term_events.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.paths.short_term_events.write_text(
            '{"valid": true}\nnot-json\n',
            encoding="utf-8",
        )

        with self.assertRaises(JsonlDecodeError):
            self.short_term_store.list_events()

    def test_tests_do_not_write_to_project_runtime(self) -> None:
        project_runtime = (
            Path(__file__).resolve().parents[2]
            / "memory"
            / "runtime"
        )

        self.assertFalse(project_runtime.exists())


if __name__ == "__main__":
    unittest.main()
