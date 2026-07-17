import tempfile
import unittest
from pathlib import Path

from memory.benchmark import run_retention_ranking_benchmark


class RetentionRankingBenchmarkTests(unittest.TestCase):
    def test_default_scenarios_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            report = run_retention_ranking_benchmark(
                runtime_root=root,
                repetitions=1,
                assessment_limit=1,
            )
            self.assertEqual(len(report["results"]), 4)
            self.assertEqual(
                report["results"][-1]["simulated_memory_count"],
                6_000_000,
            )
            self.assertFalse(root.exists())
            self.assertTrue(report["synthetic_data_only"])
            self.assertFalse(report["runtime_modified"])


if __name__ == "__main__":
    unittest.main()
