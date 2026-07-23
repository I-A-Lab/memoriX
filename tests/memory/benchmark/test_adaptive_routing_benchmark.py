import tempfile,unittest
from memory.benchmark import run_adaptive_routing_benchmark
class AdaptiveRoutingBenchmarkTests(unittest.TestCase):
 def test_bounded_scenarios(self):
  with tempfile.TemporaryDirectory() as root:
   result=run_adaptive_routing_benchmark(runtime_root=root,scenarios=(10_000,6_000_000),repetitions=1)
   self.assertEqual(len(result["results"]),2); self.assertTrue(result["dry_run"]); self.assertFalse(result["runtime_modified"])
if __name__=="__main__": unittest.main()
