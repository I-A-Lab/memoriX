from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from memory.adaptive import PressureLevel
from memory.adaptive.runtime_capacity import (
    classify_runtime_pressure,
    inspect_runtime_capacity,
)
from memory.data.paths import MemoryStoragePaths


class RuntimeCapacityTests(unittest.TestCase):
    def test_pressure_thresholds(self) -> None:
        self.assertEqual(
            classify_runtime_pressure(79, 100),
            PressureLevel.STABLE,
        )
        self.assertEqual(
            classify_runtime_pressure(80, 100),
            PressureLevel.WATCH,
        )
        self.assertEqual(
            classify_runtime_pressure(90, 100),
            PressureLevel.HIGH,
        )
        self.assertEqual(
            classify_runtime_pressure(100, 100),
            PressureLevel.CRITICAL,
        )

    def test_missing_runtime_is_empty_and_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            snapshot = inspect_runtime_capacity(
                runtime_root=root,
                configured_capacity=50_000,
            )

            self.assertFalse(root.exists())

        self.assertEqual(snapshot.active_memories, 0)
        self.assertEqual(snapshot.inactive_memories, 0)
        self.assertEqual(snapshot.pending_candidates, 0)
        self.assertEqual(snapshot.available_slots, 50_000)
        self.assertTrue(snapshot.admission_allowed)
        self.assertFalse(snapshot.simulated)
        self.assertTrue(snapshot.observation_only)
        self.assertFalse(snapshot.applies_changes)

    def test_real_metadata_uses_latest_record_per_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            paths = MemoryStoragePaths.from_runtime_root(root)
            paths.titan_metadata.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            records = (
                {"memory_id": "memory_1", "active": True},
                {"memory_id": "memory_2", "active": True},
                {"memory_id": "memory_1", "active": False},
            )
            paths.titan_metadata.write_text(
                "".join(
                    json.dumps(record) + "\n"
                    for record in records
                ),
                encoding="utf-8",
            )
            paths.memory_candidates.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            paths.memory_candidates.write_text(
                "".join(
                    (
                        json.dumps({"status": "pending"}) + "\n",
                        json.dumps({"status": "validated"}) + "\n",
                    )
                ),
                encoding="utf-8",
            )

            snapshot = inspect_runtime_capacity(
                runtime_root=root,
                configured_capacity=10,
            )

        self.assertEqual(snapshot.metadata_records, 3)
        self.assertEqual(snapshot.active_memories, 1)
        self.assertEqual(snapshot.inactive_memories, 1)
        self.assertEqual(snapshot.pending_candidates, 1)
        self.assertGreater(
            snapshot.file_sizes_bytes["titan_metadata"],
            0,
        )

    def test_six_million_item_simulation_allocates_no_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            snapshot = inspect_runtime_capacity(
                runtime_root=root,
                configured_capacity=50_000,
                simulated_active_items=6_000_000,
                simulated_inactive_items=12,
                simulated_pending_candidates=3,
            )

            self.assertFalse(root.exists())

        self.assertTrue(snapshot.simulated)
        self.assertEqual(snapshot.active_memories, 6_000_000)
        self.assertEqual(snapshot.inactive_memories, 12)
        self.assertEqual(snapshot.pending_candidates, 3)
        self.assertEqual(snapshot.available_slots, 0)
        self.assertEqual(
            snapshot.pressure_level,
            PressureLevel.CRITICAL,
        )
        self.assertFalse(snapshot.admission_allowed)
        self.assertEqual(snapshot.usage_ratio, 120.0)

    def test_repository_runtime_is_rejected(self) -> None:
        repository_runtime = (
            Path(__file__).resolve().parents[3]
            / "memory"
            / "runtime"
        )

        with self.assertRaises(ValueError):
            inspect_runtime_capacity(
                runtime_root=repository_runtime,
                configured_capacity=100,
            )

    def test_invalid_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                inspect_runtime_capacity(
                    runtime_root=directory,
                    configured_capacity=0,
                )

            with self.assertRaises(ValueError):
                inspect_runtime_capacity(
                    runtime_root=directory,
                    configured_capacity=100,
                    simulated_active_items=-1,
                )


if __name__ == "__main__":
    unittest.main()
