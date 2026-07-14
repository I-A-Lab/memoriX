from __future__ import annotations

import unittest

from memory.adaptive import (
    AdaptiveControllerInput,
    AdaptiveDecisionStatus,
    HotMemoryPruningInput,
    SoftPruningAction,
    evaluate_adaptive_controller,
)


def stable_source() -> AdaptiveControllerInput:
    block_id = "block_stable"

    return AdaptiveControllerInput(
        scope_id=block_id,
        current_capacity=100,
        used_items=30,
        usage_samples=(20, 25, 30),
        term_frequencies={
            "alpha": 4,
        },
        surprise_samples=(0.1, 0.2),
        previous_pressure_samples=(
            0.2,
            0.3,
            0.25,
        ),
        memories=(
            HotMemoryPruningInput(
                memory_id="memory_stable",
                block_id=block_id,
                importance=0.6,
                access_count=5,
                age_days=30,
                retrieval_score=0.6,
            ),
        ),
        observed_at=(
            "2026-07-14T10:00:00+00:00"
        ),
    )


def pressured_source() -> AdaptiveControllerInput:
    block_id = "block_pressured"

    return AdaptiveControllerInput(
        scope_id=block_id,
        current_capacity=100,
        used_items=95,
        usage_samples=(60, 75, 85, 95),
        term_frequencies={
            "alpha": 1,
            "beta": 1,
            "gamma": 1,
            "delta": 1,
        },
        surprise_samples=(0.8, 0.9),
        previous_pressure_samples=(
            0.80,
            0.82,
            0.85,
        ),
        memories=(
            HotMemoryPruningInput(
                memory_id="memory_pinned",
                block_id=block_id,
                importance=0.05,
                access_count=0,
                age_days=365,
                retrieval_score=0.05,
                pinned=True,
            ),
            HotMemoryPruningInput(
                memory_id="memory_weak",
                block_id=block_id,
                importance=0.30,
                access_count=1,
                age_days=280,
                retrieval_score=0.25,
            ),
            HotMemoryPruningInput(
                memory_id="memory_deactivate",
                block_id=block_id,
                importance=0.02,
                access_count=0,
                age_days=365,
                retrieval_score=0.01,
            ),
        ),
        observed_at=(
            "2026-07-14T10:00:00+00:00"
        ),
    )


class AdaptiveControllerTests(unittest.TestCase):
    def test_stable_scope_has_no_actions(
        self,
    ) -> None:
        decision = evaluate_adaptive_controller(
            stable_source(),
            decision_id="adaptive_stable",
        )

        self.assertEqual(
            decision.decision_id,
            "adaptive_stable",
        )
        self.assertEqual(
            decision.status,
            AdaptiveDecisionStatus.STABLE,
        )
        self.assertEqual(
            decision.recommended_actions,
            (),
        )
        self.assertTrue(decision.dry_run)
        self.assertFalse(decision.applied)

    def test_pressure_assembles_capacity_and_pruning(
        self,
    ) -> None:
        decision = evaluate_adaptive_controller(
            pressured_source(),
            decision_id="adaptive_pressured",
        )

        self.assertEqual(
            decision.status,
            AdaptiveDecisionStatus.ACTIONS_RECOMMENDED,
        )
        self.assertIn(
            "recommend_capacity_expansion",
            decision.recommended_actions,
        )
        self.assertIn(
            "recommend_hot_memory_weakening",
            decision.recommended_actions,
        )
        self.assertIn(
            "recommend_hot_memory_deactivation",
            decision.recommended_actions,
        )

        actions = {
            item.memory_id: item.action
            for item in (
                decision.pruning.recommendations
            )
        }

        self.assertEqual(
            actions["memory_pinned"],
            SoftPruningAction.KEEP,
        )
        self.assertEqual(
            actions["memory_weak"],
            SoftPruningAction.WEAKEN,
        )
        self.assertEqual(
            actions["memory_deactivate"],
            SoftPruningAction.DEACTIVATE,
        )

    def test_controller_preserves_safety_contracts(
        self,
    ) -> None:
        decision = evaluate_adaptive_controller(
            pressured_source()
        )

        self.assertTrue(
            decision.observation_only
        )
        self.assertTrue(decision.dry_run)
        self.assertFalse(decision.applied)
        self.assertTrue(decision.hot_site_only)
        self.assertTrue(
            decision.cold_site_untouched
        )
        self.assertFalse(
            decision.retrieval_behavior_changed
        )
        self.assertFalse(
            decision.pruning.physical_deletion
        )
        self.assertFalse(
            decision.capacity.applied
        )

    def test_blocked_actions_are_explicit(
        self,
    ) -> None:
        decision = evaluate_adaptive_controller(
            pressured_source()
        )

        self.assertIn(
            "cold_site_mutation",
            decision.blocked_actions,
        )
        self.assertIn(
            "physical_memory_deletion",
            decision.blocked_actions,
        )
        self.assertIn(
            "retrieval_contract_change",
            decision.blocked_actions,
        )
        self.assertIn(
            "automatic_candidate_validation",
            decision.blocked_actions,
        )

    def test_mismatched_memory_scope_is_rejected(
        self,
    ) -> None:
        source = AdaptiveControllerInput(
            scope_id="block_one",
            current_capacity=100,
            used_items=20,
            usage_samples=(10, 20),
            term_frequencies={},
            surprise_samples=(),
            previous_pressure_samples=(),
            memories=(
                HotMemoryPruningInput(
                    memory_id="memory_wrong",
                    block_id="block_two",
                    importance=0.5,
                    access_count=1,
                    age_days=10,
                    retrieval_score=0.5,
                ),
            ),
        )

        with self.assertRaises(ValueError):
            evaluate_adaptive_controller(
                source
            )


if __name__ == "__main__":
    unittest.main()
