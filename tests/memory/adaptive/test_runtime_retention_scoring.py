import tempfile
import unittest
from pathlib import Path

from memory.adaptive import inspect_runtime_retention_ranking


class RuntimeRetentionScoringTests(unittest.TestCase):
    def test_empty_runtime_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            report = inspect_runtime_retention_ranking(
                runtime_root=root,
            )
            self.assertEqual(report.ranking.memory_count, 0)
            self.assertFalse(root.exists())

    def test_simulation_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_runtime_retention_ranking(
                runtime_root=Path(directory) / "runtime",
                simulated_memory_count=6_000_000,
                assessment_limit=1,
            )
            self.assertEqual(report.ranking.memory_count, 6_000_000)
            self.assertEqual(len(report.ranking.assessments), 1)
            self.assertTrue(report.assessments_truncated)

    def test_report_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = inspect_runtime_retention_ranking(
                runtime_root=Path(directory) / "runtime",
            )
            self.assertTrue(report.observation_only)
            self.assertTrue(report.dry_run)
            self.assertFalse(report.applied)
            self.assertFalse(report.cold_site_accessed)
            self.assertFalse(report.neural_model_loaded)


if __name__ == "__main__":
    unittest.main()
