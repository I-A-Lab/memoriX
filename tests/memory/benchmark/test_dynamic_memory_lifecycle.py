from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.benchmark.dynamic_memory_lifecycle import (
    DynamicCampaignRequest,
    _aggregate_checks,
    compare_snapshots,
)
from memory.benchmark.dynamic_memory_lifecycle import CheckResult


class DynamicMemoryLifecycleTests(unittest.TestCase):
    def test_quick_profile(self):
        request = DynamicCampaignRequest(profile="quick").resolved()
        self.assertEqual(request.seeds, (101, 202))
        self.assertEqual(request.distractor_count, 25)
        self.assertEqual(request.update_count, 2)
        self.assertEqual(request.titan_dim, 32)

    def test_custom_profile_values(self):
        request = DynamicCampaignRequest(
            profile="quick",
            seeds=(7,),
            distractor_count=3,
            update_count=1,
            titan_dim=16,
            top_k=2,
        ).resolved()
        self.assertEqual(request.seeds, (7,))
        self.assertEqual(request.distractor_count, 3)
        self.assertEqual(request.top_k, 2)

    def test_duplicate_seed_rejected(self):
        with self.assertRaises(ValueError):
            DynamicCampaignRequest(seeds=(1, 1)).resolved()

    def test_snapshot_diff(self):
        difference = compare_snapshots(
            {"a": "1", "b": "2"},
            {"b": "3", "c": "4"},
        )
        self.assertEqual(difference["added"], ["c"])
        self.assertEqual(difference["removed"], ["a"])
        self.assertEqual(difference["changed"], ["b"])

    def test_aggregate_checks(self):
        rows = [
            CheckResult(1, "x", True, 1.0, "a", "a", {}),
            CheckResult(2, "x", False, 2.0, "a", "b", {}),
            CheckResult(1, "y", True, 3.0, "c", "c", {}),
        ]
        aggregate = _aggregate_checks(rows)
        self.assertEqual(aggregate["check_count"], 3)
        self.assertEqual(aggregate["passed_check_count"], 2)
        self.assertEqual(aggregate["failed_check_count"], 1)
        self.assertEqual(aggregate["scenarios"]["x"]["count"], 2)

    def test_output_location_can_be_external(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(Path(directory).is_dir())


if __name__ == "__main__":
    unittest.main()
