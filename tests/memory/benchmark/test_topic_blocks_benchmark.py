
from __future__ import annotations
import unittest
from memory.benchmark.topic_blocks import run_topic_block_benchmark
class TopicBlockBenchmarkTests(unittest.TestCase):
    def test_benchmark_contract(self):
        result=run_topic_block_benchmark(block_counts=(3,5),repetitions=1)
        self.assertEqual([item["block_count"] for item in result["results"]],[3,5])
        self.assertTrue(result["synthetic_data_only"])
        self.assertFalse(result["neural_model_loaded"])
if __name__=="__main__": unittest.main()
