from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.adaptive import inspect_runtime_policy_search


class RuntimePolicySearchTests(unittest.TestCase):
    def test_empty_runtime_uses_synthetic_dataset_without_creating_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent) / "missing-runtime"
            report = inspect_runtime_policy_search(runtime_root=root, max_trials=4, assessment_limit=5)
            self.assertEqual(report.status, "ok")
            self.assertEqual(report.runtime_case_count, 0)
            self.assertGreater(report.synthetic_case_count, 0)
            self.assertEqual(report.search_result.trial_count, 4)
            self.assertFalse(root.exists())
            self.assertTrue(report.dry_run)
            self.assertFalse(report.policy_applied)
            self.assertFalse(report.runtime_modified)

    def test_simulated_runtime_is_bounded_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent) / "missing-runtime"
            first = inspect_runtime_policy_search(runtime_root=root, max_trials=6, seed=7, assessment_limit=3, simulated_memory_count=6_000_000)
            second = inspect_runtime_policy_search(runtime_root=root, max_trials=6, seed=7, assessment_limit=3, simulated_memory_count=6_000_000)
            self.assertEqual(first.runtime_case_count, 3)
            self.assertEqual(first.unique_memories, 6_000_000)
            self.assertEqual(first.search_result.best_policy.policy_id, second.search_result.best_policy.policy_id)
            self.assertFalse(root.exists())
            self.assertFalse(first.cold_site_accessed)
            self.assertFalse(first.neural_model_loaded)

    def test_runtime_only_falls_back_safely_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            report = inspect_runtime_policy_search(runtime_root=Path(parent) / "none", include_synthetic_cases=False, max_trials=2)
            self.assertEqual(report.search_result.trial_count, 2)
            self.assertEqual(report.runtime_case_count, 0)
