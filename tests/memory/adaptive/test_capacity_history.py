from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    CapacityRecommendationInput,
    CapacityRecommendationStore,
    PressureObservationInput,
    observe_memory_pressure,
    recommend_dynamic_capacity,
)


class CapacityRecommendationStoreTests(
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
            / "capacity_recommendations.jsonl"
        )

        self.store = (
            CapacityRecommendationStore(
                self.path
            )
        )

    def recommendation(
        self,
        *,
        block_id: str,
        used_items: int,
    ):
        pressure = observe_memory_pressure(
            PressureObservationInput(
                scope_id=block_id,
                used_items=used_items,
                capacity=100,
                usage_samples=(
                    max(0, used_items - 20),
                    max(0, used_items - 10),
                    used_items,
                ),
                term_frequencies={
                    "alpha": 1,
                    "beta": 1,
                    "gamma": 1,
                },
                surprise_samples=(
                    0.6,
                    0.7,
                ),
                previous_pressure_samples=(
                    0.75,
                    0.80,
                    0.85,
                ),
            )
        )

        return recommend_dynamic_capacity(
            CapacityRecommendationInput(
                block_id=block_id,
                current_capacity=100,
                used_items=used_items,
                pressure=pressure,
            )
        )

    def test_missing_history_is_empty(self) -> None:
        self.assertEqual(
            self.store.read_all(),
            [],
        )

    def test_append_dry_run_recommendation(
        self,
    ) -> None:
        recommendation = self.recommendation(
            block_id="block_one",
            used_items=90,
        )

        self.store.append(recommendation)

        records = self.store.read_all()

        self.assertEqual(len(records), 1)
        self.assertTrue(
            records[0]["dry_run"]
        )
        self.assertFalse(
            records[0]["applied"]
        )

    def test_history_is_append_only(self) -> None:
        first = self.recommendation(
            block_id="block_one",
            used_items=85,
        )
        second = self.recommendation(
            block_id="block_one",
            used_items=90,
        )

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

    def test_block_filtering(self) -> None:
        self.store.append(
            self.recommendation(
                block_id="block_one",
                used_items=85,
            )
        )
        self.store.append(
            self.recommendation(
                block_id="block_two",
                used_items=90,
            )
        )

        first_block = list(
            self.store.iter_block(
                "block_one"
            )
        )

        self.assertEqual(
            len(first_block),
            1,
        )


if __name__ == "__main__":
    unittest.main()
