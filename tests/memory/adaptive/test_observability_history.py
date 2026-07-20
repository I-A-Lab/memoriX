import tempfile, unittest
from memory.adaptive import (
    MemoryHealthIndicator, MemoryMetricWindow, MemoryObservabilityCollection, MemoryObservabilityReport, MemoryObservabilityStatus,
    acknowledge_memory_observability_alert, compare_memory_observability_snapshots,
    detect_memory_observability_drift, inspect_memory_observability_state,
    list_memory_observability_alerts, list_memory_observability_snapshots,
    save_memory_observability_snapshot,
)

def report(score, alerts=()):
    collection=MemoryObservabilityCollection(samples=(),source_records=(),malformed_record_count=0,files_inspected=0,bytes_inspected=0,truncated=False,window=MemoryMetricWindow(None,None,100,8,1000000),sources_used=(),dry_run=True)
    indicator=MemoryHealthIndicator(category='runtime_integrity',score=score,status=MemoryObservabilityStatus.HEALTHY,metrics=(),reasons=())
    return MemoryObservabilityReport(overall_health_score=score,status=MemoryObservabilityStatus.HEALTHY,indicators=(indicator,),alerts=alerts,recommendations=(),insufficient_data=(),collection=collection,dry_run=True)

class ObservabilityHistoryTests(unittest.TestCase):
    def test_snapshot_is_persisted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            first=save_memory_observability_snapshot(root,snapshot_id='s1',report=report(.8))
            second=save_memory_observability_snapshot(root,snapshot_id='s1',report=report(.2))
            self.assertTrue(first.snapshot_saved); self.assertFalse(second.snapshot_saved)
            self.assertEqual(len(list_memory_observability_snapshots(root)),1)
    def test_compare_and_drift(self):
        baseline={'snapshot_id':'a','report':report(.9).to_dict()}; current={'snapshot_id':'b','report':report(.6).to_dict()}
        result=compare_memory_observability_snapshots(baseline,current,threshold=.1)
        self.assertIn('overall_health_score',result.regressed_metric_names)
    def test_insufficient_drift(self):
        with tempfile.TemporaryDirectory() as root: self.assertTrue(detect_memory_observability_drift(root).insufficient_data)
    def test_unknown_alert_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError): acknowledge_memory_observability_alert(root,alert_id='missing',actor='e',reason='x')
    def test_empty_state_read_only(self):
        with tempfile.TemporaryDirectory() as root:
            state=inspect_memory_observability_state(root); self.assertFalse(state['registry_exists'])
if __name__=='__main__': unittest.main()
