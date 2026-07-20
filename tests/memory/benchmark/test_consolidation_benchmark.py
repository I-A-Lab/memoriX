import unittest
from memory.benchmark.consolidation import run_consolidation_benchmark
class TestConsolidationBenchmark(unittest.TestCase):
 def test_report(self):
  report=run_consolidation_benchmark((10,20)); self.assertEqual(len(report['results']),2); self.assertFalse(report['neural_model_loaded'])
