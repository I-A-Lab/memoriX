from __future__ import annotations

import unittest

from memory.adaptive import (
    HotMemoryPruningInput,
    PressureObservationInput,
    SoftPruningAction,
    calculate_retention_score,
    observe_memory_pressure,
    plan_soft_pruning,
    recommend_soft_pruning,
)


def pressure_for(
    block_id: str,
    *,
    high: bool,
):
    if high:
        return observe_memory_pressure(
            PressureObservationInput(
                scope_id=block_id,
                used_items=95,
                capacity=100,
                usage_samples=(60, 75, 85, 95),
                term_frequencies={
                    "alpha": 1,
                    "beta": 1,
                    "gamma": 1,
                    "delta": 1,
                },
                surprise_samples=(0.8, 0.9),
                previous_pressure_samples=(
                    0.8,
                    0.82,
                    0.85,
                ),
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            observation_id=(
                f"pressure_{block_id}"
            ),
        )

    return observe_memory_pressure(
        PressureObservationInput(
            scope_id=block_id,
            used_items=30,
            capacity=100,
            usage_samples=(25, 28, 30),
            term_frequencies={
                "alpha": 3,
            },
            surprise_samples=(0.1, 0.2),
            previous_pressure_samples=(
                0.2,
                0.3,
                0.25,
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        observation_id=(
            f"pressure_{block_id}"
        ),
    )


class RetentionScoreTests(unittest.TestCase):
    def test_retention_score_is_normalized(
        self,
    ) -> None:
        memory = HotMemoryPruningInput(
            memory_id="memory_test",
            block_id="block_test",
            importance=0.5,
            access_count=5,
            age_days=100,
            retrieval_score=0.5,
        )

        score = calculate_retention_score(
            memory
        )

        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_recent_important_memory_scores_high(
        self,
    ) -> None:
        protected = HotMemoryPruningInput(
            memory_id="memory_protected",
            block_id="block_test",
            importance=0.95,
            access_count=25,
            age_days=1,
            retrieval_score=0.9,
        )

        weak = HotMemoryPruningInput(
            memory_id="memory_weak",
            block_id="block_test",
            importance=0.05,
            access_count=0,
            age_days=365,
            retrieval_score=0.05,
        )

        self.assertGreater(
            calculate_retention_score(protected),
            calculate_retention_score(weak),
        )


class SoftPruningRecommendationTests(
    unittest.TestCase
):
    def test_low_pressure_keeps_memory(
        self,
    ) -> None:
        block_id = "block_low"

        memory = HotMemoryPruningInput(
            memory_id="memory_low",
            block_id=block_id,
            importance=0.1,
            access_count=0,
            age_days=300,
            retrieval_score=0.1,
        )

        recommendation = (
            recommend_soft_pruning(
                memory,
                pressure_for(
                    block_id,
                    high=False,
                ),
            )
        )

        self.assertEqual(
            recommendation.action,
            SoftPruningAction.KEEP,
        )
        self.assertTrue(
            recommendation.hot_site_only
        )
        self.assertFalse(
            recommendation.physical_deletion
        )
        self.assertTrue(recommendation.dry_run)
        self.assertFalse(recommendation.applied)

    def test_pinned_memory_is_protected(
        self,
    ) -> None:
        block_id = "block_pinned"

        memory = HotMemoryPruningInput(
            memory_id="memory_pinned",
            block_id=block_id,
            importance=0.05,
            access_count=0,
            age_days=365,
            retrieval_score=0.05,
            pinned=True,
        )

        recommendation = (
            recommend_soft_pruning(
                memory,
                pressure_for(
                    block_id,
                    high=True,
                ),
            )
        )

        self.assertEqual(
            recommendation.action,
            SoftPruningAction.KEEP,
        )
        self.assertTrue(
            recommendation.protected
        )
        self.assertIn(
            "pinned",
            recommendation.protection_reasons,
        )

    def test_recent_memory_is_protected(
        self,
    ) -> None:
        block_id = "block_recent"

        memory = HotMemoryPruningInput(
            memory_id="memory_recent",
            block_id=block_id,
            importance=0.1,
            access_count=0,
            age_days=2,
            retrieval_score=0.05,
        )

        recommendation = (
            recommend_soft_pruning(
                memory,
                pressure_for(
                    block_id,
                    high=True,
                ),
            )
        )

        self.assertEqual(
            recommendation.action,
            SoftPruningAction.KEEP,
        )
        self.assertIn(
            "recent",
            recommendation.protection_reasons,
        )

    def test_low_retention_can_weaken(
        self,
    ) -> None:
        block_id = "block_weaken"

        memory = HotMemoryPruningInput(
            memory_id="memory_weaken",
            block_id=block_id,
            importance=0.30,
            access_count=1,
            age_days=280,
            retrieval_score=0.25,
        )

        recommendation = (
            recommend_soft_pruning(
                memory,
                pressure_for(
                    block_id,
                    high=True,
                ),
            )
        )

        self.assertEqual(
            recommendation.action,
            SoftPruningAction.WEAKEN,
        )

    def test_very_low_retention_can_deactivate(
        self,
    ) -> None:
        block_id = "block_deactivate"

        memory = HotMemoryPruningInput(
            memory_id="memory_deactivate",
            block_id=block_id,
            importance=0.02,
            access_count=0,
            age_days=365,
            retrieval_score=0.01,
        )

        recommendation = (
            recommend_soft_pruning(
                memory,
                pressure_for(
                    block_id,
                    high=True,
                ),
            )
        )

        self.assertEqual(
            recommendation.action,
            SoftPruningAction.DEACTIVATE,
        )
        self.assertFalse(
            recommendation.physical_deletion
        )


class SoftPruningPlanTests(unittest.TestCase):
    def test_plan_is_hot_only_and_unapplied(
        self,
    ) -> None:
        block_id = "block_plan"

        memories = (
            HotMemoryPruningInput(
                memory_id="memory_keep",
                block_id=block_id,
                importance=0.95,
                access_count=25,
                age_days=1,
                retrieval_score=0.9,
            ),
            HotMemoryPruningInput(
                memory_id="memory_deactivate",
                block_id=block_id,
                importance=0.01,
                access_count=0,
                age_days=365,
                retrieval_score=0.01,
            ),
        )

        plan = plan_soft_pruning(
            scope_id=block_id,
            memories=memories,
            pressure=pressure_for(
                block_id,
                high=True,
            ),
            plan_id="pruning_test",
            created_at=(
                "2026-07-14T11:00:00+00:00"
            ),
        )

        self.assertEqual(
            plan.plan_id,
            "pruning_test",
        )
        self.assertTrue(plan.hot_site_only)
        self.assertTrue(
            plan.cold_site_untouched
        )
        self.assertFalse(
            plan.physical_deletion
        )
        self.assertTrue(plan.dry_run)
        self.assertFalse(plan.applied)
        self.assertEqual(
            len(plan.recommendations),
            2,
        )

    def test_duplicate_memory_ids_are_rejected(
        self,
    ) -> None:
        block_id = "block_duplicate"

        memory = HotMemoryPruningInput(
            memory_id="memory_duplicate",
            block_id=block_id,
            importance=0.5,
            access_count=1,
            age_days=30,
            retrieval_score=0.5,
        )

        with self.assertRaises(ValueError):
            plan_soft_pruning(
                scope_id=block_id,
                memories=(memory, memory),
                pressure=pressure_for(
                    block_id,
                    high=True,
                ),
            )


if __name__ == "__main__":
    unittest.main()
