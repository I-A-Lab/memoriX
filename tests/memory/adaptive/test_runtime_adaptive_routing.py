import tempfile, unittest
from pathlib import Path
from memory.adaptive import inspect_runtime_adaptive_routing

class RuntimeAdaptiveRoutingTests(unittest.TestCase):
    def test_empty_runtime_admits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing"
            r=inspect_runtime_adaptive_routing(runtime_root=p,target_id="c1",configured_capacity=10)
            self.assertEqual(r.plan.decision.decision.value,"admit")
            self.assertFalse(p.exists())
            self.assertTrue(r.dry_run)
    def test_simulated_full_runtime_is_non_mutating(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing"
            r=inspect_runtime_adaptive_routing(runtime_root=p,target_id="c1",retention_score=.9,configured_capacity=10,simulated_memory_count=10,assessment_limit=1)
            self.assertIn(r.plan.decision.decision.value,{"admit_after_pruning","reject_safely"})
            self.assertFalse(r.runtime_modified)
            self.assertFalse(p.exists())
if __name__=="__main__": unittest.main()
