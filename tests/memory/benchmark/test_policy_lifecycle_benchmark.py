
from __future__ import annotations
import unittest
from memory.benchmark import run_policy_lifecycle_benchmark
class PolicyLifecycleBenchmarkTests(unittest.TestCase):
    def test_bounded_synthetic_benchmark(self):
        result=run_policy_lifecycle_benchmark(counts=(2,5),repetitions=1)
        self.assertEqual([x["version_count"] for x in result["results"]],[2,5]); self.assertFalse(result["neural_model_loaded"])
if __name__ == "__main__": unittest.main()
