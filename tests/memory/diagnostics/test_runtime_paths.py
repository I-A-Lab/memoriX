from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.data.paths import MemoryStoragePaths
from memory.diagnostics.live_probe import discover_runtime_paths


class RuntimePathDiscoveryTests(unittest.TestCase):
    def test_uses_canonical_memory_storage_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            runtime_root = Path(temp_directory)
            storage_paths = (
                MemoryStoragePaths.from_runtime_root(runtime_root)
            )

            discovered = discover_runtime_paths(runtime_root)

            self.assertEqual(
                discovered["runtime_root"],
                storage_paths.runtime_root,
            )
            self.assertEqual(
                discovered["short_term_events"],
                storage_paths.short_term_events,
            )
            self.assertEqual(
                discovered["cold_archive_events"],
                storage_paths.cold_archive_events,
            )
            self.assertEqual(
                discovered["memory_candidates"],
                storage_paths.memory_candidates,
            )
            self.assertEqual(
                discovered["titan_neural_state"],
                storage_paths.titan_neural_state,
            )
            self.assertEqual(
                discovered["titan_metadata"],
                storage_paths.titan_metadata,
            )
            self.assertEqual(
                discovered["nightly_logs"],
                storage_paths.nightly_logs,
            )

    def test_discovery_does_not_create_runtime_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            runtime_root = Path(temp_directory)

            before = tuple(runtime_root.rglob("*"))
            discover_runtime_paths(runtime_root)
            after = tuple(runtime_root.rglob("*"))

            self.assertEqual(before, ())
            self.assertEqual(after, ())

    def test_old_incorrect_paths_are_not_returned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            runtime_root = Path(temp_directory)
            discovered = discover_runtime_paths(runtime_root)
            discovered_values = set(discovered.values())

            forbidden_paths = {
                runtime_root / "cold" / "events.jsonl",
                runtime_root / "cold" / "archive.jsonl",
                runtime_root / "candidates" / "pending.jsonl",
                runtime_root / "candidates" / "validated.jsonl",
                runtime_root / "hot" / "memories.json",
                runtime_root / "hot" / "titan_state.pt",
            }

            self.assertTrue(
                discovered_values.isdisjoint(forbidden_paths)
            )


if __name__ == "__main__":
    unittest.main()
