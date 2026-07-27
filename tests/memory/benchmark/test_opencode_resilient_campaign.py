from __future__ import annotations

import unittest

from memory.benchmark.opencode_resilient_campaign import (
    ResilientCampaignRequest,
    _aggregate,
    _parse_tools,
    _technical_failure_reason,
)


class ResilientCampaignTests(unittest.TestCase):
    def test_large_profile(self):
        request = (
            ResilientCampaignRequest(
                profile="large"
            ).resolved()
        )
        self.assertEqual(
            request.seeds,
            (101, 202, 303),
        )
        self.assertEqual(
            request.task_count,
            8,
        )
        self.assertEqual(
            request.distractor_count,
            1000,
        )

    def test_transient_provider_error(self):
        reason = _technical_failure_reason(
            exit_code=1,
            timed_out=False,
            stdout=(
                '{"type":"error",'
                '"message":"No provider available"}'
            ),
            stderr="",
            tool_calls=0,
            text_events=0,
        )
        self.assertEqual(
            reason,
            "provider_or_network_unavailable",
        )

    def test_success_is_technically_valid(self):
        reason = _technical_failure_reason(
            exit_code=0,
            timed_out=False,
            stdout="",
            stderr="",
            tool_calls=1,
            text_events=1,
        )
        self.assertIsNone(reason)

    def test_all_memory_tools_are_counted(self):
        stdout = "\n".join(
            [
                '{"type":"tool_use","part":{"tool":"read"}}',
                '{"type":"tool_use","part":{"tool":"memory_retrieve"}}',
                '{"type":"tool_use","part":{"tool":"memory_candidates_list"}}',
                '{"type":"tool_use","part":{"tool":"project_snapshot_get"}}',
            ]
        )
        count, tools = _parse_tools(stdout)
        self.assertEqual(count, 3)
        self.assertEqual(
            tools,
            (
                "memory_retrieve",
                "memory_candidates_list",
                "project_snapshot_get",
            ),
        )

    def test_invalid_pair_is_excluded(self):
        rows = [
            {
                "seed": 1,
                "kind": "x",
                "mode": "no_memory",
                "technical_valid": False,
                "exit_code": 1,
                "timed_out": False,
                "task_passed": False,
                "case_count": 0,
                "passed_case_count": 0,
                "duration_ms": 1.0,
                "tool_calls": 0,
                "memory_retrieve_calls": 0,
                "memory_tool_calls": 0,
                "retry_count": 2,
                "attempt_count": 3,
            },
            {
                "seed": 1,
                "kind": "x",
                "mode": "memorix_core",
                "technical_valid": True,
                "exit_code": 0,
                "timed_out": False,
                "task_passed": True,
                "case_count": 2,
                "passed_case_count": 2,
                "duration_ms": 2.0,
                "tool_calls": 2,
                "memory_retrieve_calls": 1,
                "memory_tool_calls": 1,
                "retry_count": 0,
                "attempt_count": 1,
            },
        ]
        aggregate = _aggregate(rows)
        paired = aggregate[
            "paired_comparison"
        ]
        self.assertEqual(
            paired["valid_pair_count"],
            0,
        )
        self.assertEqual(
            paired["invalid_pair_count"],
            1,
        )
        self.assertEqual(
            paired["memorix_wins"],
            0,
        )

    def test_valid_pair_is_compared(self):
        base = {
            "technical_valid": True,
            "exit_code": 0,
            "timed_out": False,
            "case_count": 3,
            "duration_ms": 1.0,
            "tool_calls": 1,
            "memory_retrieve_calls": 0,
            "memory_tool_calls": 0,
            "retry_count": 0,
            "attempt_count": 1,
        }
        rows = [
            {
                **base,
                "seed": 1,
                "kind": "x",
                "mode": "no_memory",
                "task_passed": False,
                "passed_case_count": 2,
            },
            {
                **base,
                "seed": 1,
                "kind": "x",
                "mode": "memorix_core",
                "task_passed": True,
                "passed_case_count": 3,
                "memory_retrieve_calls": 1,
                "memory_tool_calls": 1,
            },
        ]
        aggregate = _aggregate(rows)
        paired = aggregate[
            "paired_comparison"
        ]
        self.assertEqual(
            paired["valid_pair_count"],
            1,
        )
        self.assertEqual(
            paired["memorix_wins"],
            1,
        )

    def test_invalid_retry_configuration(self):
        with self.assertRaises(ValueError):
            ResilientCampaignRequest(
                max_attempts=0
            ).resolved()


if __name__ == "__main__":
    unittest.main()
