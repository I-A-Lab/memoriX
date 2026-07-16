from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.data import (
    MemoryStoragePaths,
    ProjectArchiveEntry,
    ProjectArchiveEntryType,
    ProjectSnapshot,
)


class ProjectArchiveEntryContractTests(unittest.TestCase):
    def make_entry(self) -> ProjectArchiveEntry:
        return ProjectArchiveEntry(
            entry_id="project_entry_001",
            project_id="memorix",
            entry_type=ProjectArchiveEntryType.DECISION,
            title="Keep cold history append-only",
            content="Project archive entries are immutable append-only records.",
            source_event_ids=("event_project_001",),
            author="Elwen",
            created_at="2026-07-16T10:00:00+00:00",
            recorded_at="2026-07-16T10:05:00+00:00",
            metadata={"scope": "project_archive"},
        )

    def test_round_trip(self) -> None:
        entry = self.make_entry()
        self.assertEqual(ProjectArchiveEntry.from_dict(entry.to_dict()), entry)

    def test_requires_source_event(self) -> None:
        with self.assertRaises(ValueError):
            ProjectArchiveEntry(
                project_id="memorix",
                entry_type=ProjectArchiveEntryType.NOTE,
                title="Missing source",
                content="Invalid archive entry.",
                source_event_ids=(),
                author="Elwen",
            )

    def test_rejects_unknown_entry_type(self) -> None:
        with self.assertRaises(ValueError):
            ProjectArchiveEntry(
                project_id="memorix",
                entry_type="unknown",
                title="Unknown",
                content="Unknown type.",
                source_event_ids=("event_001",),
                author="Elwen",
            )


class ProjectSnapshotContractTests(unittest.TestCase):
    def make_snapshot(self) -> ProjectSnapshot:
        return ProjectSnapshot(
            project_id="memorix",
            name="memoriX",
            summary="Long-term memory for AI agents.",
            objectives=("Provide durable project memory.",),
            decisions=("Cold history remains audit-only.",),
            architecture=("Hot and cold sites stay separated.",),
            milestones=("OpenCode integration completed.",),
            completed_tasks=("Step 16 completed.",),
            remaining_tasks=("Implement Project Archive.",),
            problems=("Project history was unstructured.",),
            solutions=("Add explicit archive contracts.",),
            latest_changes=("Runtime moved outside repository.",),
            source_entry_ids=("project_entry_001",),
            version=1,
            updated_at="2026-07-16T10:10:00+00:00",
        )

    def test_round_trip(self) -> None:
        snapshot = self.make_snapshot()
        self.assertEqual(ProjectSnapshot.from_dict(snapshot.to_dict()), snapshot)

    def test_rejects_invalid_version(self) -> None:
        with self.assertRaises(ValueError):
            ProjectSnapshot(
                project_id="memorix",
                name="memoriX",
                summary="Invalid version.",
                version=0,
            )


class ProjectArchivePathTests(unittest.TestCase):
    def test_paths_are_inside_cold_project_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = MemoryStoragePaths.from_runtime_root(temporary)
            expected_root = Path(temporary).resolve() / "cold_site" / "project_archive"
            self.assertEqual(paths.project_archive_entries, expected_root / "project_entries.jsonl")
            self.assertEqual(paths.project_archive_snapshots, expected_root / "project_snapshots.jsonl")

    def test_path_resolution_creates_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = MemoryStoragePaths.from_runtime_root(temporary)
            self.assertFalse(paths.project_archive_entries.exists())
            self.assertFalse(paths.project_archive_snapshots.exists())


if __name__ == "__main__":
    unittest.main()
