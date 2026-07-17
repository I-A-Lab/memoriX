from __future__ import annotations

import math
import unittest

from memory.adaptive.retention_scoring import (
    RetentionScoringInput,
    RetentionScoringThresholds,
    RetentionScoringWeights,
    assess_adaptive_retention,
    calculate_adaptive_retention_score,
    rank_hot_site_memories,
)


class RetentionScoringTests(unittest.TestCase):
    def test_weights_require_one_positive_scoring_weight(self) -> None:
        with self.assertRaises(ValueError):
            RetentionScoringWeights(
                importance=0.0,
                recency=0.0,
                usage=0.0,
                retrieval=0.0,
                confidence=0.0,
                momentum=0.0,
                surprise=0.0,
            ).validate()

    def test_thresholds_must_be_ordered(self) -> None:
        with self.assertRaises(ValueError):
            RetentionScoringThresholds(
                keep=0.4,
                watch=0.7,
                review=0.2,
            ).validate()

    def test_score_is_deterministic_and_bounded(self) -> None:
        source = RetentionScoringInput(
            memory_id="memory",
            age_days=30,
            access_count=5,
            importance=0.8,
            retrieval_score=0.7,
            confidence=0.9,
            momentum=0.4,
            surprise=0.6,
        )
        first, first_components = calculate_adaptive_retention_score(source)
        second, second_components = calculate_adaptive_retention_score(source)
        self.assertEqual(first, second)
        self.assertEqual(first_components, second_components)
        self.assertGreaterEqual(first, 0.0)
        self.assertLessEqual(first, 1.0)

    def test_non_finite_normalized_inputs_are_safe(self) -> None:
        score, components = calculate_adaptive_retention_score(
            RetentionScoringInput(
                memory_id="non-finite",
                importance=float("nan"),
                retrieval_score=float("inf"),
                confidence=float("-inf"),
                momentum=float("nan"),
                surprise=float("inf"),
            )
        )
        self.assertTrue(math.isfinite(score))
        self.assertTrue(all(math.isfinite(value) for value in components.to_dict().values()))

    def test_inactive_and_replaced_penalties_lower_retention(self) -> None:
        baseline = RetentionScoringInput(
            memory_id="baseline",
            age_days=10,
            access_count=10,
            importance=0.7,
            retrieval_score=0.7,
            confidence=0.7,
            momentum=0.7,
            surprise=0.7,
        )
        penalized = RetentionScoringInput(
            memory_id="penalized",
            age_days=10,
            access_count=10,
            importance=0.7,
            retrieval_score=0.7,
            confidence=0.7,
            momentum=0.7,
            surprise=0.7,
            active=False,
            replaced=True,
        )
        baseline_score, _ = calculate_adaptive_retention_score(baseline)
        penalized_score, _ = calculate_adaptive_retention_score(penalized)
        self.assertLess(penalized_score, baseline_score)

    def test_protected_memory_is_always_kept(self) -> None:
        result = assess_adaptive_retention(
            RetentionScoringInput(
                memory_id="protected",
                age_days=730,
                access_count=0,
                importance=0.0,
                retrieval_score=0.0,
                confidence=0.0,
                momentum=0.0,
                surprise=0.0,
                replaced=True,
                protected=True,
            ),
            assessment_id="assessment",
        )
        self.assertEqual(result.recommended_action, "keep_protected")
        self.assertIn("explicitly_protected", result.protection_reasons)
        self.assertTrue(result.protected)

    def test_unvalidated_memory_is_protected(self) -> None:
        result = assess_adaptive_retention(
            RetentionScoringInput(
                memory_id="pending",
                human_validated=False,
            )
        )
        self.assertEqual(result.recommended_action, "keep_protected")
        self.assertIn("not_human_validated", result.protection_reasons)

    def test_low_quality_memory_explains_risks(self) -> None:
        result = assess_adaptive_retention(
            RetentionScoringInput(
                memory_id="low",
                age_days=730,
                access_count=0,
                importance=0.0,
                retrieval_score=0.0,
                confidence=0.0,
                momentum=0.0,
                surprise=0.0,
                replaced=True,
            )
        )
        self.assertEqual(result.recommended_action, "deactivate_candidate")
        self.assertIn("low_importance", result.risk_reasons)
        self.assertIn("old", result.risk_reasons)
        self.assertIn("replaced", result.risk_reasons)
        self.assertTrue(result.observation_only)
        self.assertTrue(result.dry_run)
        self.assertFalse(result.applied)
        self.assertFalse(result.cold_site_accessed)
        self.assertFalse(result.neural_model_loaded)

    def test_high_quality_memory_explains_strengths(self) -> None:
        result = assess_adaptive_retention(
            RetentionScoringInput(
                memory_id="high",
                age_days=0,
                access_count=20,
                importance=1.0,
                retrieval_score=1.0,
                confidence=1.0,
                momentum=1.0,
                surprise=1.0,
            )
        )
        self.assertEqual(result.recommended_action, "keep")
        self.assertIn("high_importance", result.reasons)
        self.assertIn("frequently_accessed", result.reasons)
        self.assertIn("strong_retrieval", result.reasons)

    def test_ranking_is_descending_and_ties_use_memory_id(self) -> None:
        ranking = rank_hot_site_memories(
            (
                RetentionScoringInput(memory_id="z", importance=0.5),
                RetentionScoringInput(memory_id="a", importance=0.5),
                RetentionScoringInput(
                    memory_id="best",
                    age_days=0,
                    access_count=20,
                    importance=1.0,
                    retrieval_score=1.0,
                    confidence=1.0,
                    momentum=1.0,
                    surprise=1.0,
                ),
            ),
            observed_at="2026-07-17T00:00:00+00:00",
            ranking_id="ranking",
        )
        self.assertEqual(
            [item.memory_id for item in ranking.assessments],
            ["best", "a", "z"],
        )
        self.assertEqual(
            [item.rank for item in ranking.assessments],
            [1, 2, 3],
        )

    def test_ranking_rejects_duplicate_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate memory_id"):
            rank_hot_site_memories(
                (
                    RetentionScoringInput(memory_id="duplicate"),
                    RetentionScoringInput(memory_id="duplicate"),
                )
            )

    def test_empty_ranking_is_safe(self) -> None:
        ranking = rank_hot_site_memories(
            (),
            observed_at="2026-07-17T00:00:00+00:00",
            ranking_id="empty",
        )
        self.assertEqual(ranking.memory_count, 0)
        self.assertEqual(ranking.mean_retention, 0.0)
        self.assertEqual(ranking.maximum_retention, 0.0)
        self.assertEqual(ranking.minimum_retention, 0.0)
        self.assertEqual(ranking.assessments, ())

    def test_ranking_summary_counts_actions_and_protection(self) -> None:
        ranking = rank_hot_site_memories(
            (
                RetentionScoringInput(memory_id="protected", protected=True),
                RetentionScoringInput(
                    memory_id="weak",
                    age_days=730,
                    importance=0.0,
                    retrieval_score=0.0,
                    confidence=0.0,
                    replaced=True,
                ),
            )
        )
        self.assertEqual(ranking.protected_count, 1)
        self.assertEqual(ranking.action_counts["keep_protected"], 1)
        self.assertEqual(ranking.action_counts["deactivate_candidate"], 1)
        self.assertTrue(ranking.observation_only)
        self.assertTrue(ranking.dry_run)
        self.assertFalse(ranking.applied)
        self.assertFalse(ranking.cold_site_accessed)
        self.assertFalse(ranking.neural_model_loaded)


if __name__ == "__main__":
    unittest.main()
