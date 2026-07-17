from __future__ import annotations
from pathlib import Path
import tempfile
import unittest
from memory.benchmark import run_memory_pressure_benchmark
class MemoryPressureBenchmarkTests(unittest.TestCase):
 def test_scenarios_are_bounded_and_read_only(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/"runtime"; payload=run_memory_pressure_benchmark(runtime_root=root,repetitions=1)
   self.assertFalse(root.exists())
  self.assertEqual([x["simulated_memory_count"] for x in payload["results"]],[10000,100000,1000000,6000000]); self.assertTrue(payload["synthetic_data_only"]); self.assertFalse(payload["runtime_modified"]); self.assertTrue(all(x["assessment_count"]<=1 for x in payload["results"]))
 def test_invalid_repetitions(self):
  with tempfile.TemporaryDirectory() as directory:
   with self.assertRaises(ValueError): run_memory_pressure_benchmark(runtime_root=directory,repetitions=0)
if __name__=="__main__": unittest.main()
