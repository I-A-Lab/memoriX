from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    PressureHistoryStore,
    PressureObservationInput,
    observe_memory_pressure,
)


class PressureHistoryStoreTests(unittest.TestCase):
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
            / "pressure_history.jsonl"
        )

        self.store = PressureHistoryStore(
            self.path
        )

    def test_missing_history_is_empty(self) -> None:
        self.assertEqual(
            self.store.read_all(),
            [],
        )

    def test_append_and_read_observation(self) -> None:
        observation = observe_memory_pressure(
            PressureObservationInput(
                scope_id="hot_site",
                used_items=40,
                capacity=100,
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            observation_id="pressure_one",
        )

        self.store.append(observation)

        records = self.store.read_all()

        self.assertEqual(len(records), 1)
        self.assertEqual(
            records[0]["observation_id"],
            "pressure_one",
        )
        self.assertEqual(
            records[0]["scope_id"],
            "hot_site",
        )
        self.assertTrue(
            records[0]["observation_only"]
        )

    def test_scope_filtering(self) -> None:
        for scope_id in (
            "block_music",
            "block_code",
            "block_music",
        ):
            self.store.append(
                observe_memory_pressure(
                    PressureObservationInput(
                        scope_id=scope_id,
                        used_items=1,
                        capacity=10,
                        observed_at=(
                            "2026-07-14T10:00:00+00:00"
                        ),
                    )
                )
            )

        music_records = list(
            self.store.iter_scope(
                "block_music"
            )
        )

        self.assertEqual(
            len(music_records),
            2,
        )

    def test_history_is_append_only(self) -> None:
        first = observe_memory_pressure(
            PressureObservationInput(
                scope_id="hot_site",
                used_items=10,
                capacity=100,
            ),
            observation_id="pressure_first",
        )

        second = observe_memory_pressure(
            PressureObservationInput(
                scope_id="hot_site",
                used_items=20,
                capacity=100,
            ),
            observation_id="pressure_second",
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


if __name__ == "__main__":
    unittest.main()
