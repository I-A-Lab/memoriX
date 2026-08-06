from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.retrieval_correction import (
    _evaluate,
    validate_diagnostic_report,
)

class RetrievalCorrectionTests(unittest.TestCase):
    def test_negative_query_is_not_trivially_exact(self):
        queries = [{
            "query_id": "q1",
            "family": "forget",
            "query": "forgotten",
            "expected_record_ids": [],
            "forbidden_record_ids": ["r1"],
            "expected_value": None,
        }]
        metrics, rows, families = _evaluate(
            queries,
            lambda query: [{"record_id": "r1"}],
        )
        self.assertEqual(metrics.negative_exclusion_rate, 0.0)
        self.assertTrue(rows[0]["forbidden_hit"])
        self.assertEqual(
            families["forget"]["negative_exclusion_rate"],
            0.0,
        )

    def test_positive_metrics_ignore_negative_queries(self):
        queries = [
            {
                "query_id": "q1",
                "family": "project_fact",
                "query": "key",
                "expected_record_ids": ["r1"],
                "forbidden_record_ids": [],
                "expected_value": "v1",
            },
            {
                "query_id": "q2",
                "family": "forget",
                "query": "forgotten",
                "expected_record_ids": [],
                "forbidden_record_ids": ["r2"],
                "expected_value": None,
            },
        ]
        def retrieve(query):
            if query["query_id"] == "q1":
                return [{
                    "record_id": "r1",
                    "canonical_fact": {"value": "v1"},
                }]
            return []
        metrics, _, _ = _evaluate(queries, retrieve)
        self.assertEqual(metrics.positive_recall_at_1, 1.0)
        self.assertEqual(metrics.positive_exact_value_rate, 1.0)
        self.assertEqual(metrics.negative_exclusion_rate, 1.0)

    def test_validator_rejects_wrong_run_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text(
                '{"version":"40.6.1","campaign":"retrieval_diagnostic",'
                '"seeds":[1,2],"run_count":5}',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_diagnostic_report(path)

if __name__ == "__main__":
    unittest.main()
