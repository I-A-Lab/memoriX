from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    HotMemoryPruningInput,
    PressureObservationInput,
    SoftPruningPlanStore,
    observe_memory_pressure,
    plan_soft_pruning,
)


class SoftPruningPlanStoreTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.path = (
            Path(
                self.temporary_directory.name
            )
            / "adaptive"
            / "pruning_plans.jsonl"
        )

        self.store = SoftPruningPlanStore(
            self.path
        )

    def plan(self, scope_id: str):
        pressure = observe_memory_pressure(
            PressureObservationInput(
                scope_id=scope_id,
                used_items=95,
                capacity=100,
                usage_samples=(60, 75, 85, 95),
                term_frequencies={
                    "alpha": 1,
                    "beta": 1,
                    "gamma": 1,
                },
                surprise_samples=(0.8, 0.9),
                previous_pressure_samples=(
                    0.8,
                    0.82,
                    0.85,
                ),
            )
        )

        memory = HotMemoryPruningInput(
            memory_id=f"memory_{scope_id}",
            block_id=scope_id,
            importance=0.05,
            access_count=0,
            age_days=365,
            retrieval_score=0.05,
        )

        return plan_soft_pruning(
            scope_id=scope_id,
            memories=(memory,),
            pressure=pressure,
        )

    def test_missing_history_is_empty(self) -> None:
        self.assertEqual(
            self.store.read_all(),
            [],
        )

    def test_append_dry_run_plan(self) -> None:
        plan = self.plan("block_one")

        self.store.append(plan)

        records = self.store.read_all()

        self.assertEqual(len(records), 1)
        self.assertTrue(
            records[0]["hot_site_only"]
        )
        self.assertTrue(
            records[0]["cold_site_untouched"]
        )
        self.assertFalse(
            records[0]["physical_deletion"]
        )
        self.assertTrue(
            records[0]["dry_run"]
        )
        self.assertFalse(
            records[0]["applied"]
        )

    def test_history_is_append_only(self) -> None:
        first = self.plan("block_one")
        second = self.plan("block_two")

        self.store.append(first)
        first_bytes = self.path.read_bytes()

        self.store.append(second)
        second_bytes = self.path.read_bytes()

        self.assertTrue(
            second_bytes.startswith(first_bytes)
        )
        self.assertEqual(
            len(self.store.read_all()),
            2,
        )

    def test_scope_filtering(self) -> None:
        self.store.append(
            self.plan("block_one")
        )
        self.store.append(
            self.plan("block_two")
        )

        matches = list(
            self.store.iter_scope(
                "block_one"
            )
        )

        self.assertEqual(
            len(matches),
            1,
        )


if __name__ == "__main__":
    unittest.main()
