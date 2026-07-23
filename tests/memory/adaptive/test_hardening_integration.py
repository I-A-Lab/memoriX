from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from memory.adaptive.active_policy import load_active_memory_policy
from memory.adaptive.consolidation_operations import execute_memory_consolidation, register_memory_consolidation_plan, review_memory_consolidation
from memory.adaptive.observability import collect_memory_observability_samples
from memory.adaptive.runtime_adaptive_routing import inspect_runtime_adaptive_routing
from memory.adaptive.runtime_retention_scoring import inspect_runtime_retention_ranking
from memory.adaptive.topic_schema import normalize_topic_assignment_record, normalize_topic_block_record

class HardeningIntegrationTests(unittest.TestCase):
    def write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(record) + '\n' for record in records), encoding='utf-8')

    def test_active_policy_is_applied_to_retention_and_routing(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)
            policy={"policy_id":"strict","description":"strict","retention_weights":{},"retention_thresholds":{"keep":0.95,"watch":0.9,"review":0.8},"routing_policy":{"minimum_admission_score":0.9,"high_priority_score":0.95,"soft_pruning_score":0.8,"maximum_pruning_items":10}}
            self.write_jsonl(root/'policies/policy_versions.jsonl',[{"version_id":"v1","policy":policy,"status":"active","created_at":"2026-01-01T00:00:00+00:00","created_by":"test","source":"test"}])
            (root/'policies/policy_state.json').write_text(json.dumps({"active_policy_version_id":"v1","previous_policy_version_id":None,"pending_proposal_ids":[]}),encoding='utf-8')
            self.write_jsonl(root/'hot_site/titan_metadata.jsonl',[{"memory_id":"m1","active":True,"metadata":{"importance":0.5}}])
            active=load_active_memory_policy(root)
            self.assertEqual(active.version_id,'v1')
            ranking=inspect_runtime_retention_ranking(runtime_root=root)
            routing=inspect_runtime_adaptive_routing(runtime_root=root,target_id='candidate',retention_score=0.5,configured_capacity=10)
            self.assertEqual(ranking.active_policy_version_id,'v1')
            self.assertEqual(routing.active_policy_version_id,'v1')
            self.assertFalse(routing.plan.decision.allowed)

    def test_consolidation_deactivates_duplicates_and_archives_them(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)
            self.write_jsonl(root/'hot_site/titan_metadata.jsonl',[{"memory_id":"m1","content":"same fact","active":True},{"memory_id":"m2","content":"same fact","active":True}])
            register_memory_consolidation_plan(root,plan_id='p1')
            review_memory_consolidation(root,plan_id='p1',approved=True,actor='human',reason='ok',validation_id='v1')
            result=execute_memory_consolidation(root,plan_id='p1',session_id='s1',actor='human',reason='ok',validation_id='v1')
            self.assertTrue(result.consolidation_executed)
            self.assertGreaterEqual(result.memories_updated,1)
            self.assertTrue((root/'cold_site/consolidated_memories.jsonl').is_file())

    def test_observability_filters_time_and_reports_retrieval_metrics(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)
            self.write_jsonl(root/'hot_site/titan_metadata.jsonl',[{"memory_id":"old","stored_at":"2025-01-01T00:00:00+00:00","metadata":{"access_count":9,"retrieval_score":0.9}},{"memory_id":"new","stored_at":"2026-01-01T00:00:00+00:00","metadata":{"access_count":2,"retrieval_score":0.5}}])
            result=collect_memory_observability_samples(root,start_time='2025-12-01T00:00:00+00:00')
            values={sample.metric_name:sample.metric_value for sample in result.samples}
            self.assertEqual(dict(result.source_records)['hot_metadata'],1)
            self.assertEqual(values['retrieval_access_count'],2.0)
            self.assertEqual(values['mean_retrieval_score'],0.5)

    def test_topic_records_are_canonical(self):
        block=normalize_topic_block_record({'label':'Coding','used_items':3})
        assignment=normalize_topic_assignment_record({'item_id':'m1','target_block_id':'block_coding'})
        self.assertEqual(block['memory_count'],3)
        self.assertEqual(block['block_id'],block['topic_block_id'])
        self.assertEqual(assignment['block_id'],assignment['topic_block_id'])

if __name__ == '__main__': unittest.main()
