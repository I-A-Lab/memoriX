from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.benchmark.opencode_real_campaign import (
    CampaignRequest,
    TASK_KINDS,
    _aggregate,
    build_task,
    build_tasks,
    compare_snapshots,
    evaluate_solution,
)


class OpenCodeRealCampaignTests(unittest.TestCase):
    def test_profile_resolution(self):
        request = CampaignRequest(
            profile="small",
            model="provider/model",
        ).resolved()
        self.assertEqual(request.seeds, (101, 202, 303))
        self.assertEqual(request.task_count, 4)
        self.assertEqual(request.distractor_count, 50)
        self.assertEqual(request.model, "provider/model")

    def test_smoke_allows_configured_default_model(self):
        request = CampaignRequest(profile="smoke", model=None).resolved()
        self.assertIsNone(request.model)

    def test_small_allows_configured_default_model(self):
        request = CampaignRequest(profile="small", model=None).resolved()
        self.assertIsNone(request.model)

    def test_decisions_vary_with_seed(self):
        first = build_task("csv_delimiter", 101)
        variants = {
            build_task("csv_delimiter", seed).decision_text
            for seed in range(101, 120)
        }
        self.assertGreater(len(variants), 1)
        self.assertNotIn(first.decision_text, first.prompt)

    def test_task_count_matches_profile(self):
        request = CampaignRequest(profile="smoke", model=None).resolved()
        tasks = build_tasks(request)
        self.assertEqual(len(tasks), len(request.seeds) * request.task_count)
        self.assertEqual([task.kind for task in tasks], list(TASK_KINDS[:2]))

    def test_hidden_evaluator_accepts_correct_csv_solution(self):
        task = build_task("csv_delimiter", 101)
        delimiter = task.expected["delimiter"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solution.py"
            path.write_text(
                "def serialize_rows(rows):\n"
                f"    return '\\n'.join({delimiter!r}.join(str(cell) for cell in row) for row in rows)\n",
                encoding="utf-8",
            )
            result = evaluate_solution(task, path)
            self.assertTrue(result["passed"])

    def test_hidden_evaluator_rejects_wrong_decision(self):
        task = build_task("page_size", 101)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solution.py"
            path.write_text(
                "def normalize_page_size(requested):\n"
                "    return 999\n",
                encoding="utf-8",
            )
            result = evaluate_solution(task, path)
            self.assertFalse(result["passed"])

    def test_snapshot_comparison_detects_changes(self):
        result = compare_snapshots(
            {"a.py": "1", "b.py": "2"},
            {"a.py": "9", "c.py": "3"},
        )
        self.assertEqual(result["changed"], ["a.py"])
        self.assertEqual(result["removed"], ["b.py"])
        self.assertEqual(result["added"], ["c.py"])

    def test_aggregate_uses_paired_results(self):
        rows = [
            {
                "seed": 1,
                "kind": "a",
                "mode": "no_memory",
                "task_passed": False,
                "case_count": 2,
                "passed_case_count": 0,
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 10,
                "tool_calls": 1,
                "memory_retrieve_calls": 0,
            },
            {
                "seed": 1,
                "kind": "a",
                "mode": "memorix_core",
                "task_passed": True,
                "case_count": 2,
                "passed_case_count": 2,
                "exit_code": 0,
                "timed_out": False,
                "duration_ms": 20,
                "tool_calls": 2,
                "memory_retrieve_calls": 1,
            },
        ]
        result = _aggregate(rows)
        self.assertEqual(result["paired_comparison"]["memorix_wins"], 1)
        self.assertEqual(result["memorix_core"]["memory_retrieve_call_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
