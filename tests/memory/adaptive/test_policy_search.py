from __future__ import annotations

import unittest

from memory.adaptive import (
    AdaptiveRoutingDecisionType,
    MemoryPolicyCandidate,
    MemoryPolicyDataset,
    MemoryPolicyEvaluationCase,
    MemoryPolicySearchConfig,
    MemoryPolicySearchSpace,
    RetentionScoringInput,
    RetentionScoringThresholds,
    RetentionScoringWeights,
    AdaptiveRoutingPolicy,
    default_memory_policy_dataset,
    default_memory_policy_search_space,
    evaluate_memory_policy,
    search_memory_policies,
)


class MemoryPolicySearchTests(unittest.TestCase):
    def test_default_search_space_is_bounded(self) -> None:
        space = default_memory_policy_search_space()
        self.assertEqual(len(space.candidates), 12)
        self.assertEqual(len({item.policy_id for item in space.candidates}), 12)

    def test_default_dataset_covers_expected_cases(self) -> None:
        dataset = default_memory_policy_dataset()
        self.assertGreaterEqual(len(dataset.cases), 9)
        self.assertTrue(any(case.protected_safety_case for case in dataset.cases))
        self.assertTrue(any(case.low_value_case for case in dataset.cases))
        self.assertTrue(any(case.expected_routing_decision is AdaptiveRoutingDecisionType.ADMIT_AFTER_PRUNING for case in dataset.cases))

    def test_candidate_validation_rejects_empty_id(self) -> None:
        candidate = MemoryPolicyCandidate(
            policy_id="",
            retention_weights=RetentionScoringWeights(),
            retention_thresholds=RetentionScoringThresholds(),
            routing_policy=AdaptiveRoutingPolicy(),
        )
        with self.assertRaises(ValueError):
            candidate.validate()

    def test_dataset_rejects_duplicate_cases(self) -> None:
        case = MemoryPolicyEvaluationCase(
            case_id="duplicate",
            retention_input=RetentionScoringInput(memory_id="one"),
            expected_retention_action="watch",
        )
        with self.assertRaises(ValueError):
            MemoryPolicyDataset(cases=(case, case)).validate()

    def test_evaluation_is_deterministic(self) -> None:
        candidate = default_memory_policy_search_space().candidates[0]
        dataset = default_memory_policy_dataset()
        first = evaluate_memory_policy(candidate, dataset)
        second = evaluate_memory_policy(candidate, dataset)
        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.passed_case_ids, second.passed_case_ids)

    def test_metrics_are_bounded(self) -> None:
        trial = evaluate_memory_policy(
            default_memory_policy_search_space().candidates[0],
            default_memory_policy_dataset(),
        )
        values = trial.metrics.to_dict()
        self.assertTrue(all(0.0 <= value <= 1.0 for value in values.values()))

    def test_search_honors_trial_limit(self) -> None:
        result = search_memory_policies(config=MemoryPolicySearchConfig(max_trials=5, seed=1))
        self.assertEqual(result.trial_count, 5)
        self.assertEqual(len(result.trials), 5)

    def test_search_is_reproducible_for_seed(self) -> None:
        config = MemoryPolicySearchConfig(max_trials=8, seed=7)
        first = search_memory_policies(config=config)
        second = search_memory_policies(config=config)
        self.assertEqual(first.best_policy.policy_id, second.best_policy.policy_id)
        self.assertEqual(first.best_score, second.best_score)
        self.assertEqual([trial.policy.policy_id for trial in first.trials], [trial.policy.policy_id for trial in second.trials])

    def test_ranked_trials_are_descending(self) -> None:
        result = search_memory_policies()
        scores = [trial.metrics.combined_score for trial in result.trials]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_best_policy_matches_first_trial(self) -> None:
        result = search_memory_policies()
        self.assertEqual(result.best_policy.policy_id, result.trials[0].policy.policy_id)
        self.assertEqual(result.best_score, result.trials[0].metrics.combined_score)

    def test_result_explains_selection_and_default_difference(self) -> None:
        result = search_memory_policies()
        self.assertIn("highest_combined_score", result.selection_reasons)
        self.assertIn("retention_weights.importance", result.difference_from_default)
        self.assertIn("routing_policy.minimum_admission_score", result.difference_from_default)

    def test_search_is_strictly_action_free(self) -> None:
        result = search_memory_policies()
        self.assertTrue(result.dry_run)
        self.assertFalse(result.runtime_modified)
        self.assertFalse(result.cold_site_accessed)
        self.assertFalse(result.neural_model_loaded)
        self.assertFalse(result.pruning_executed)
        self.assertFalse(result.candidate_validated)
        for trial in result.trials:
            self.assertTrue(trial.dry_run)
            self.assertFalse(trial.runtime_modified)
            self.assertFalse(trial.cold_site_accessed)
            self.assertFalse(trial.neural_model_loaded)
            self.assertFalse(trial.pruning_executed)
            self.assertFalse(trial.candidate_validated)

    def test_custom_single_policy_search(self) -> None:
        candidate = default_memory_policy_search_space().candidates[0]
        result = search_memory_policies(
            search_space=MemoryPolicySearchSpace(candidates=(candidate,)),
            config=MemoryPolicySearchConfig(max_trials=1, seed=99),
        )
        self.assertEqual(result.trial_count, 1)
        self.assertEqual(result.best_policy.policy_id, candidate.policy_id)


if __name__ == "__main__":
    unittest.main()
