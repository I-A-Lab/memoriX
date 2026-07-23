from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    AdaptiveControllerInput,
    AdaptiveDecisionStore,
    HotMemoryPruningInput,
    evaluate_adaptive_controller,
)


class AdaptiveDecisionStoreTests(
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
            / "controller_decisions.jsonl"
        )

        self.store = AdaptiveDecisionStore(
            self.path
        )

    def decision(self, scope_id: str):
        source = AdaptiveControllerInput(
            scope_id=scope_id,
            current_capacity=100,
            used_items=30,
            usage_samples=(20, 25, 30),
            term_frequencies={
                "alpha": 1,
            },
            surprise_samples=(0.2,),
            previous_pressure_samples=(
                0.2,
                0.3,
            ),
            memories=(
                HotMemoryPruningInput(
                    memory_id=f"memory_{scope_id}",
                    block_id=scope_id,
                    importance=0.5,
                    access_count=2,
                    age_days=30,
                    retrieval_score=0.5,
                ),
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        return evaluate_adaptive_controller(
            source
        )

    def test_missing_history_is_empty(self) -> None:
        self.assertEqual(
            self.store.read_all(),
            [],
        )

    def test_append_dry_run_decision(
        self,
    ) -> None:
        decision = self.decision(
            "block_one"
        )

        self.store.append(decision)

        records = self.store.read_all()

        self.assertEqual(len(records), 1)
        self.assertTrue(
            records[0]["observation_only"]
        )
        self.assertTrue(
            records[0]["dry_run"]
        )
        self.assertFalse(
            records[0]["applied"]
        )
        self.assertTrue(
            records[0]["cold_site_untouched"]
        )

    def test_history_is_append_only(self) -> None:
        first = self.decision("block_one")
        second = self.decision("block_two")

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
            self.decision("block_one")
        )
        self.store.append(
            self.decision("block_two")
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
