from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from memory.benchmark.memory_pure_benchmark import DeterministicLexicalEngine, run_pure_memory_benchmark, write_results

class TestPureMemoryBenchmark(unittest.TestCase):
    def fixture(self,root:Path):
        records=[{'record_id':'r1','active':True,'should_retrieve':True,'content':'alpha key_one=value_one','canonical_fact':{'key':'key_one','value':'value_one'}},{'record_id':'r2','active':False,'should_retrieve':False,'content':'forgotten key_two=value_two','canonical_fact':{'key':'key_two','value':'value_two'}}]
        queries=[{'query_id':'q1','family':'user_profile','query':'current key_one','expected_record_ids':['r1'],'forbidden_record_ids':[],'expected_value':'value_one'},{'query_id':'q2','family':'forget','query':'current key_two','expected_record_ids':[],'forbidden_record_ids':['r2'],'expected_value':None}]
        for name,rows in [('records.jsonl',records),('queries.jsonl',queries)]: (root/name).write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    def test_metrics_are_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root); a,_=run_pure_memory_benchmark(root,DeterministicLexicalEngine()); b,_=run_pure_memory_benchmark(root,DeterministicLexicalEngine())
            self.assertEqual(a.recall_at_1,b.recall_at_1); self.assertEqual(a.forbidden_hit_rate,0.0)
    def test_forget_query_does_not_return_inactive_record(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root); _,rows=run_pure_memory_benchmark(root,DeterministicLexicalEngine()); self.assertFalse(rows[1]['forbidden_hit'])
    def test_top_k_must_be_positive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); self.fixture(root)
            with self.assertRaises(ValueError): run_pure_memory_benchmark(root,DeterministicLexicalEngine(),top_k=0)
    def test_write_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=root/'data'; data.mkdir(); self.fixture(data); metrics,rows=run_pure_memory_benchmark(data,DeterministicLexicalEngine()); out=root/'out'; write_results(out,metrics,rows,engine_name='lexical',dataset_id='x')
            with self.assertRaises(FileExistsError): write_results(out,metrics,rows,engine_name='lexical',dataset_id='x')
    def test_report_contains_sha256(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=root/'data'; data.mkdir(); self.fixture(data); metrics,rows=run_pure_memory_benchmark(data,DeterministicLexicalEngine()); report=write_results(root/'out',metrics,rows,engine_name='lexical',dataset_id='x'); payload=json.loads(report.read_text()); self.assertEqual(len(payload['query_results_sha256']),64)
if __name__=='__main__': unittest.main()
