from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import (
    MemoryStoragePaths,
    ProjectArchiveEntryType,
)
from memory.gateway import MemoriXGateway


class ProjectArchiveGatewayTests(unittest.TestCase):
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
            titan_d_model=16,
            titan_hidden_dim=16,
            titan_max_items=50,
            titan_device="cpu",
            titan_top_k=3,
            titan_min_score=0.0,
        )

    def record_identity(self):
        return self.gateway.record_project_archive_entry(
            entry_id="project_entry_identity",
            project_id="memorix",
            entry_type=ProjectArchiveEntryType.IDENTITY,
            title="memoriX",
            content="Long-term memory for AI agents.",
            source_event_ids=(
                "event_project_identity",
            ),
            author="Elwen",
            created_at="2026-07-16T13:00:00+00:00",
            recorded_at="2026-07-16T13:01:00+00:00",
        )

    def test_records_and_lists_project_entries(
        self,
    ) -> None:
        entry = self.record_identity()

        listed = (
            self.gateway.list_project_archive_entries(
                project_id="memorix"
            )
        )

        self.assertEqual(listed, (entry,))
        self.assertTrue(
            self.paths.project_archive_entries.is_file()
        )
        self.assertFalse(
            self.paths.titan_neural_state.exists()
        )
        self.assertFalse(
            self.paths.titan_metadata.exists()
        )

    def test_rebuilds_and_reads_latest_snapshot(
        self,
    ) -> None:
        self.record_identity()

        self.gateway.record_project_archive_entry(
            entry_id="project_entry_objective",
            project_id="memorix",
            entry_type="objective",
            title="Objective",
            content="Provide durable project memory.",
            source_event_ids=(
                "event_project_objective",
            ),
            author="Elwen",
            created_at="2026-07-16T13:02:00+00:00",
            recorded_at="2026-07-16T13:03:00+00:00",
        )

        snapshot = (
            self.gateway.rebuild_project_snapshot(
                "memorix",
                updated_at=(
                    "2026-07-16T13:05:00+00:00"
                ),
            )
        )

        latest = self.gateway.get_project_snapshot(
            "memorix"
        )

        self.assertEqual(latest, snapshot)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(
            snapshot.objectives,
            ("Provide durable project memory.",),
        )
        self.assertTrue(
            self.paths.project_archive_snapshots.is_file()
        )
        self.assertFalse(
            self.paths.titan_neural_state.exists()
        )

    def test_status_reports_project_archive(
        self,
    ) -> None:
        self.record_identity()
        self.gateway.rebuild_project_snapshot(
            "memorix",
            updated_at="2026-07-16T13:05:00+00:00",
        )

        status = self.gateway.memory_status()

        self.assertEqual(
            status["project_archive_entries"],
            1,
        )
        self.assertEqual(
            status["project_archive_snapshots"],
            1,
        )
        self.assertEqual(
            status["paths"]["project_archive_entries"],
            str(
                self.paths.project_archive_entries
            ),
        )
        self.assertEqual(
            status["hot_memories_total"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
