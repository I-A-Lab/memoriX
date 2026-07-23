from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    TopicBlockInput,
    TopicBlockRegistry,
    observe_topic_block,
)


class TopicBlockRegistryTests(unittest.TestCase):
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
            / "topic_blocks.json"
        )

        self.registry = TopicBlockRegistry(
            self.path
        )

    def observation(
        self,
        *,
        content: str,
        item_id: str,
        metadata_terms: tuple[str, ...] = (),
        observed_at: str,
    ):
        return observe_topic_block(
            TopicBlockInput(
                content=content,
                item_id=item_id,
                metadata_terms=metadata_terms,
                capacity=10,
                used_items=1,
                observed_at=observed_at,
            )
        )

    def test_missing_registry_is_empty(self) -> None:
        state = self.registry.read()

        self.assertEqual(
            state["blocks"],
            [],
        )
        self.assertTrue(
            state["observation_only"]
        )

    def test_first_observation_creates_block(
        self,
    ) -> None:
        observation = self.observation(
            content=(
                "astronomy astronomy telescope"
            ),
            item_id="item_one",
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        stored = self.registry.upsert_observation(
            observation
        )

        self.assertEqual(
            stored["block_id"],
            observation.block_id,
        )
        self.assertEqual(
            stored["observation_count"],
            1,
        )
        self.assertEqual(
            stored["observed_item_ids"],
            ["item_one"],
        )

    def test_same_dynamic_block_is_merged(
        self,
    ) -> None:
        first = self.observation(
            content=(
                "astronomy astronomy telescope"
            ),
            item_id="item_one",
            metadata_terms=("astronomy",),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        second = self.observation(
            content=(
                "astronomy astronomy stars"
            ),
            item_id="item_two",
            metadata_terms=("astronomy",),
            observed_at=(
                "2026-07-14T11:00:00+00:00"
            ),
        )

        self.assertEqual(
            first.block_id,
            second.block_id,
        )

        self.registry.upsert_observation(first)
        merged = self.registry.upsert_observation(
            second
        )

        self.assertEqual(
            merged["observation_count"],
            2,
        )
        self.assertEqual(
            merged["observed_item_ids"],
            [
                "item_one",
                "item_two",
            ],
        )
        self.assertEqual(
            merged["used_items"],
            2,
        )
        self.assertEqual(
            merged["usage_ratio"],
            0.2,
        )
        self.assertTrue(
            merged["observation_only"]
        )

    def test_different_topics_create_blocks(
        self,
    ) -> None:
        astronomy = self.observation(
            content=(
                "astronomy astronomy telescope"
            ),
            item_id="item_space",
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        )

        cooking = self.observation(
            content=(
                "cooking cooking recipe kitchen"
            ),
            item_id="item_food",
            observed_at=(
                "2026-07-14T11:00:00+00:00"
            ),
        )

        self.registry.upsert_observation(
            astronomy
        )
        self.registry.upsert_observation(
            cooking
        )

        blocks = self.registry.blocks()

        self.assertEqual(
            len(blocks),
            2,
        )

    def test_registry_is_deterministically_sorted(
        self,
    ) -> None:
        observations = [
            self.observation(
                content="zebra zebra animal",
                item_id="item_z",
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            self.observation(
                content="alpha alpha system",
                item_id="item_a",
                observed_at=(
                    "2026-07-14T11:00:00+00:00"
                ),
            ),
        ]

        for observation in observations:
            self.registry.upsert_observation(
                observation
            )

        identifiers = [
            block["block_id"]
            for block in self.registry.blocks()
        ]

        self.assertEqual(
            identifiers,
            sorted(identifiers),
        )


if __name__ == "__main__":
    unittest.main()
