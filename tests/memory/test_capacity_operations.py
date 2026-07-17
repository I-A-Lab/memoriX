from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from memory.gateway.capacity_operations import CapacityOperationLockedError, CapacityOperations

class CapacityOperationsTests(unittest.TestCase):
    def test_records_latest_and_history(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); ops=CapacityOperations(lock_path=root/'capacity.lock', events_path=root/'events.jsonl', latest_path=root/'latest.json')
            event=ops.record('capacity_checked', {'active_items': 3})
            self.assertEqual(event['event_type'], 'capacity_checked')
            self.assertTrue((root/'events.jsonl').exists())
            self.assertTrue((root/'latest.json').exists())
    def test_lock_rejects_concurrent_mutation(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); ops=CapacityOperations(lock_path=root/'capacity.lock', events_path=root/'events.jsonl', latest_path=root/'latest.json')
            with ops.mutation_lock('prune'):
                with self.assertRaises(CapacityOperationLockedError):
                    with ops.mutation_lock('prune'): pass
            self.assertFalse((root/'capacity.lock').exists())
if __name__ == '__main__': unittest.main()
