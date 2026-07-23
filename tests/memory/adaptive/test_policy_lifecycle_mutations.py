
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from memory.adaptive import (
    MemoryPolicyLifecycleStatus,
    activate_memory_policy,
    inspect_memory_policy_registry,
    plan_memory_policy_activation,
    plan_memory_policy_rollback,
    propose_memory_policy,
    review_memory_policy,
    rollback_memory_policy,
    search_memory_policies,
)

class PolicyLifecycleMutationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def propose(self, version_id="v1"):
        return propose_memory_policy(self.root, search_memory_policies(), proposal_id=version_id, created_by="tester", created_at="2026-07-20T00:00:00+00:00")

    def approve(self, version_id="v1"):
        return review_memory_policy(self.root, version_id=version_id, approved=True, reviewed_by="reviewer", reason="validated", validation_id=f"validation-{version_id}")

    def test_propose_persists_pending_version(self):
        result=self.propose(); self.assertTrue(result.ok); self.assertTrue(result.policy_proposed)
        snapshot=inspect_memory_policy_registry(self.root)
        self.assertEqual(snapshot.pending_proposal_ids,("v1",)); self.assertEqual(snapshot.versions[0].status,MemoryPolicyLifecycleStatus.PROPOSED)

    def test_duplicate_proposal_is_rejected(self):
        self.propose(); result=self.propose(); self.assertFalse(result.ok); self.assertEqual(result.message,"proposal_already_exists")

    def test_approve_does_not_activate(self):
        self.propose(); result=self.approve(); self.assertTrue(result.policy_approved); self.assertFalse(result.policy_activated)
        self.assertIsNone(inspect_memory_policy_registry(self.root).active_policy_version_id)

    def test_reject_removes_pending(self):
        self.propose(); result=review_memory_policy(self.root,version_id="v1",approved=False,reviewed_by="reviewer",reason="unsafe",validation_id="reject-1")
        self.assertTrue(result.policy_rejected); self.assertEqual(inspect_memory_policy_registry(self.root).pending_proposal_ids,())

    def test_activation_requires_approval(self):
        self.propose(); plan=plan_memory_policy_activation(self.root,"v1"); self.assertFalse(plan.allowed); self.assertIn("policy_not_approved",plan.blocking_reasons)

    def test_activate_approved_policy(self):
        self.propose(); self.approve(); result=activate_memory_policy(self.root,version_id="v1",activated_by="operator",reason="release",validation_id="activate-1")
        self.assertTrue(result.policy_activated); self.assertEqual(inspect_memory_policy_registry(self.root).active_policy_version_id,"v1")

    def test_activate_second_and_rollback(self):
        self.propose("v1"); self.approve("v1"); activate_memory_policy(self.root,version_id="v1",activated_by="operator",reason="first",validation_id="a1")
        self.propose("v2"); self.approve("v2"); activate_memory_policy(self.root,version_id="v2",activated_by="operator",reason="second",validation_id="a2")
        plan=plan_memory_policy_rollback(self.root); self.assertTrue(plan.allowed); self.assertEqual(plan.target_version_id,"v1")
        result=rollback_memory_policy(self.root,rolled_back_by="operator",reason="regression",validation_id="r1")
        self.assertTrue(result.policy_rolled_back); self.assertEqual(inspect_memory_policy_registry(self.root).active_policy_version_id,"v1")

    def test_registry_files_are_atomic_and_parseable(self):
        self.propose(); self.approve()
        policy_dir=self.root/"policies"
        self.assertTrue((policy_dir/"policy_versions.jsonl").is_file()); self.assertTrue((policy_dir/"policy_state.json").is_file())
        self.assertFalse(any(policy_dir.glob("*.tmp")))

if __name__ == "__main__": unittest.main()
