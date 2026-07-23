from __future__ import annotations

import math
import unittest

from memory.adaptive import (
    AdaptiveRoutingDecisionType,
    AdaptiveRoutingInput,
    AdaptiveRoutingPolicy,
    RoutingPruningCandidate,
    decide_adaptive_routing,
    plan_adaptive_routing,
)


class AdaptiveRoutingPolicyTests(unittest.TestCase):
    def test_available_capacity_admits_validated_candidate(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                retention_score=0.8,
                configured_capacity=10,
                active_memories=8,
            ),
            decision_id="decision-1",
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.ADMIT,
        )
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_permission)

    def test_unvalidated_candidate_is_deferred(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                human_validated=False,
                configured_capacity=10,
                active_memories=1,
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.DEFER,
        )
        self.assertIn(
            "candidate_not_human_validated",
            decision.blocking_reasons,
        )

    def test_low_score_full_capacity_is_deferred(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                retention_score=0.2,
                configured_capacity=10,
                active_memories=10,
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.DEFER,
        )
        self.assertEqual(
            decision.recommended_next_step,
            "keep_candidate_pending",
        )

    def test_prunable_capacity_requires_permission(self) -> None:
        source = AdaptiveRoutingInput(
            target_id="candidate-1",
            retention_score=0.9,
            configured_capacity=10,
            active_memories=10,
            pruning_candidates=(
                RoutingPruningCandidate(
                    memory_id="old-2",
                    retention_score=0.1,
                ),
                RoutingPruningCandidate(
                    memory_id="old-1",
                    retention_score=0.0,
                ),
            ),
        )
        decision = decide_adaptive_routing(source)
        plan = plan_adaptive_routing(
            source,
            plan_id="plan-1",
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING,
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_permission)
        self.assertEqual(
            plan.pruning_memory_ids,
            ("old-1",),
        )
        self.assertFalse(plan.pruning_executed)

    def test_insufficient_prunable_capacity_rejects_safely(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                retention_score=0.9,
                configured_capacity=10,
                active_memories=11,
                required_slots=2,
                pruning_candidates=(
                    RoutingPruningCandidate(
                        memory_id="protected",
                        retention_score=0.0,
                        protected=True,
                    ),
                ),
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.REJECT_SAFELY,
        )
        self.assertIn(
            "insufficient_prunable_memories",
            decision.blocking_reasons,
        )

    def test_protected_candidate_is_protected_when_capacity_exists(
        self,
    ) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                protected=True,
                configured_capacity=10,
                active_memories=1,
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.PROTECT,
        )
        self.assertTrue(decision.allowed)

    def test_existing_memory_is_kept(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="memory-1",
                target_kind="memory",
                retention_score=0.7,
                configured_capacity=10,
                active_memories=10,
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.KEEP,
        )

    def test_weak_existing_memory_is_reviewed_only(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="memory-1",
                target_kind="memory",
                retention_score=0.1,
                configured_capacity=10,
                active_memories=10,
            )
        )

        self.assertEqual(
            decision.decision,
            AdaptiveRoutingDecisionType.REVIEW_FOR_SOFT_PRUNING,
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_permission)

    def test_plan_is_deterministic(self) -> None:
        source = AdaptiveRoutingInput(
            target_id="candidate-1",
            retention_score=0.9,
            configured_capacity=2,
            active_memories=2,
            pruning_candidates=(
                RoutingPruningCandidate(
                    memory_id="z",
                    retention_score=0.1,
                ),
                RoutingPruningCandidate(
                    memory_id="a",
                    retention_score=0.1,
                ),
            ),
            observed_at="2026-07-19T00:00:00+00:00",
        )

        first = plan_adaptive_routing(
            source,
            decision_id="decision",
            plan_id="plan",
        )
        second = plan_adaptive_routing(
            source,
            decision_id="decision",
            plan_id="plan",
        )

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.pruning_memory_ids, ("a",))

    def test_non_finite_scores_are_normalized(self) -> None:
        decision = decide_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                retention_score=math.nan,
                importance=math.inf,
                confidence=-math.inf,
                configured_capacity=10,
                active_memories=0,
            )
        )

        self.assertEqual(
            decision.context.retention_score,
            0.5,
        )
        self.assertEqual(decision.context.importance, 0.5)
        self.assertEqual(decision.context.confidence, 0.5)

    def test_policy_validation_rejects_invalid_order(self) -> None:
        with self.assertRaises(ValueError):
            AdaptiveRoutingPolicy(
                minimum_admission_score=0.2,
                high_priority_score=0.1,
            ).validate()

    def test_plan_never_mutates_runtime_or_cold_site(self) -> None:
        plan = plan_adaptive_routing(
            AdaptiveRoutingInput(
                target_id="candidate-1",
                configured_capacity=1,
                active_memories=0,
            )
        )

        payload = plan.to_dict()
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["applied"])
        self.assertFalse(payload["candidate_validated"])
        self.assertFalse(payload["pruning_executed"])
        self.assertFalse(payload["runtime_modified"])
        self.assertFalse(payload["cold_site_accessed"])
        self.assertFalse(payload["neural_model_loaded"])


if __name__ == "__main__":
    unittest.main()
