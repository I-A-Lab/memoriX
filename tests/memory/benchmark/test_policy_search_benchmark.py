import tempfile, unittest
from memory.benchmark import run_policy_search_benchmark
class PolicySearchBenchmarkTests(unittest.TestCase):
    def test_four_bounded_scenarios(self):
        with tempfile.TemporaryDirectory() as directory:
            report=run_policy_search_benchmark(runtime_root=directory, repetitions=1)
            self.assertEqual([row["simulated_memory_count"] for row in report.results], [10000,100000,1000000,6000000])
            self.assertTrue(report.dry_run)
            self.assertFalse(report.runtime_modified)
if __name__ == "__main__": unittest.main()
