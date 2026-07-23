import tempfile, unittest
from pathlib import Path
from memory.adaptive import configure_memory_consolidation_schedule, execute_memory_consolidation, inspect_memory_consolidation_state, recover_memory_consolidation_session, register_memory_consolidation_plan, review_memory_consolidation
class ConsolidationOperationsTests(unittest.TestCase):
 def test_plan_review_execute(self):
  with tempfile.TemporaryDirectory() as root:
   self.assertTrue(register_memory_consolidation_plan(root,plan_id='p1').ok)
   self.assertTrue(review_memory_consolidation(root,plan_id='p1',approved=True,actor='e',reason='ok',validation_id='v').ok)
   result=execute_memory_consolidation(root,plan_id='p1',session_id='s1',actor='e',reason='ok',validation_id='v')
   self.assertTrue(result.consolidation_executed); self.assertEqual(inspect_memory_consolidation_state(root)['state']['last_status'],'completed')
 def test_schedule_and_recovery_noop(self):
  with tempfile.TemporaryDirectory() as root:
   self.assertTrue(configure_memory_consolidation_schedule(root,frequency='daily',actor='e').ok)
   self.assertEqual(recover_memory_consolidation_session(root,actor='e',reason='none').message,'no_recovery_required')
if __name__=='__main__': unittest.main()
