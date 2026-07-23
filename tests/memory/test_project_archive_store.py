from __future__ import annotations

import tempfile
import unittest

from memory.cold_site.project_archive import (
    DuplicateProjectArchiveEntryError,
    DuplicateProjectSnapshotVersionError,
    MissingProjectIdentityError,
    ProjectArchiveService,
    ProjectArchiveStore,
)
from memory.data import (
    MemoryStoragePaths,
    ProjectArchiveEntry,
    ProjectArchiveEntryType,
)


class ProjectArchiveTestCase(unittest.TestCase):
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
        self.store = ProjectArchiveStore(
            entries_path=(
                self.paths.project_archive_entries
            ),
            snapshots_path=(
                self.paths.project_archive_snapshots
            ),
        )
        self.service = ProjectArchiveService(
            self.store
        )

    @staticmethod
    def entry(
        *,
        entry_id: str,
        entry_type: ProjectArchiveEntryType,
        title: str,
        content: str,
    ) -> ProjectArchiveEntry:
        return ProjectArchiveEntry(
            entry_id=entry_id,
            project_id="memorix",
            entry_type=entry_type,
            title=title,
            content=content,
            source_event_ids=(
                f"event_{entry_id}",
            ),
            author="Elwen",
            created_at="2026-07-16T12:00:00+00:00",
            recorded_at="2026-07-16T12:01:00+00:00",
        )


class ProjectArchiveStoreTests(ProjectArchiveTestCase):
    def test_missing_files_are_empty(self) -> None:
        self.assertEqual(
            self.store.list_entries(),
            (),
        )
        self.assertEqual(
            self.store.list_snapshots(),
            (),
        )

    def test_append_entry_is_durable(self) -> None:
        entry = self.entry(
            entry_id="project_entry_identity",
            entry_type=ProjectArchiveEntryType.IDENTITY,
            title="memoriX",
            content="Memory system for AI agents.",
        )

        self.store.append_entry(entry)

        self.assertEqual(
            self.store.list_entries(),
            (entry,),
        )
        self.assertTrue(
            self.paths.project_archive_entries.is_file()
        )

    def test_duplicate_entry_is_rejected(self) -> None:
        entry = self.entry(
            entry_id="project_entry_duplicate",
            entry_type=ProjectArchiveEntryType.NOTE,
            title="Note",
            content="One append-only note.",
        )

        self.store.append_entry(entry)

        with self.assertRaises(
            DuplicateProjectArchiveEntryError
        ):
            self.store.append_entry(entry)

    def test_filters_entries_by_project_and_type(
        self,
    ) -> None:
        identity = self.entry(
            entry_id="project_entry_identity",
            entry_type=ProjectArchiveEntryType.IDENTITY,
            title="memoriX",
            content="Memory system.",
        )
        decision = self.entry(
            entry_id="project_entry_decision",
            entry_type=ProjectArchiveEntryType.DECISION,
            title="Decision",
            content="Keep history append-only.",
        )

        self.store.append_entry(identity)
        self.store.append_entry(decision)

        self.assertEqual(
            self.store.list_entries(
                project_id="memorix",
                entry_type=ProjectArchiveEntryType.DECISION,
            ),
            (decision,),
        )


class ProjectSnapshotServiceTests(ProjectArchiveTestCase):
    def test_snapshot_requires_identity(self) -> None:
        self.service.record_entry(
            self.entry(
                entry_id="project_entry_decision",
                entry_type=ProjectArchiveEntryType.DECISION,
                title="Decision",
                content="Keep history append-only.",
            )
        )

        with self.assertRaises(
            MissingProjectIdentityError
        ):
            self.service.rebuild_snapshot("memorix")

    def test_rebuild_snapshot_is_deterministic(
        self,
    ) -> None:
        identity = self.entry(
            entry_id="project_entry_identity",
            entry_type=ProjectArchiveEntryType.IDENTITY,
            title="memoriX",
            content="Memory system for AI agents.",
        )
        objective = self.entry(
            entry_id="project_entry_objective",
            entry_type=ProjectArchiveEntryType.OBJECTIVE,
            title="Objective",
            content="Provide durable project memory.",
        )
        decision = self.entry(
            entry_id="project_entry_decision",
            entry_type=ProjectArchiveEntryType.DECISION,
            title="Decision",
            content="Keep history append-only.",
        )

        for entry in (
            identity,
            objective,
            decision,
        ):
            self.service.record_entry(entry)

        snapshot = self.service.rebuild_snapshot(
            "memorix",
            updated_at="2026-07-16T12:05:00+00:00",
        )

        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.name, "memoriX")
        self.assertEqual(
            snapshot.objectives,
            ("Provide durable project memory.",),
        )
        self.assertEqual(
            snapshot.decisions,
            ("Keep history append-only.",),
        )
        self.assertEqual(
            snapshot.source_entry_ids,
            (
                identity.entry_id,
                objective.entry_id,
                decision.entry_id,
            ),
        )

    def test_snapshot_versions_are_append_only(
        self,
    ) -> None:
        self.service.record_entry(
            self.entry(
                entry_id="project_entry_identity",
                entry_type=ProjectArchiveEntryType.IDENTITY,
                title="memoriX",
                content="Memory system.",
            )
        )

        first = self.service.rebuild_snapshot(
            "memorix",
            updated_at="2026-07-16T12:05:00+00:00",
        )
        second = self.service.rebuild_snapshot(
            "memorix",
            updated_at="2026-07-16T12:10:00+00:00",
        )

        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 2)
        self.assertEqual(
            self.store.latest_snapshot("memorix"),
            second,
        )
        self.assertEqual(
            len(
                self.store.list_snapshots(
                    project_id="memorix"
                )
            ),
            2,
        )

    def test_duplicate_snapshot_version_is_rejected(
        self,
    ) -> None:
        self.service.record_entry(
            self.entry(
                entry_id="project_entry_identity",
                entry_type=ProjectArchiveEntryType.IDENTITY,
                title="memoriX",
                content="Memory system.",
            )
        )

        snapshot = self.service.rebuild_snapshot(
            "memorix",
            updated_at="2026-07-16T12:05:00+00:00",
        )

        with self.assertRaises(
            DuplicateProjectSnapshotVersionError
        ):
            self.store.append_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
