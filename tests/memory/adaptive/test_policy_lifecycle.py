from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.adaptive import (
    MemoryPolicyLifecycleStatus,
    MemoryPolicyMetrics,
    MemoryPolicyVersion,
    audit_memory_policy_lifecycle,
    compare_memory_policy_versions,
    default_memory_policy_search_space,
    inspect_memory_policy_registry,
    preview_memory_policy_proposal,
    search_memory_policies,
)


class PolicyLifecyclePlanningTests(unittest.TestCase):
    def test_audit_reports_missing_lifecycle(self) -> None:
        audit = audit_memory_policy_lifecycle()
        self.assertFalse(audit.persistence_present)
        self.assertFalse(audit.activation_present)
        self.assertTrue(audit.dry_run)

    def test_version_round_trip(self) -> None:
        candidate = default_memory_policy_search_space().candidates[0]
        version = MemoryPolicyVersion(
            version_id="policy-v1",
            policy=candidate,
            status=MemoryPolicyLifecycleStatus.ACTIVE,
            created_at="2026-07-20T00:00:00+00:00",
            created_by="tester",
            source="test",
        )
        restored = MemoryPolicyVersion.from_dict(version.to_dict())
        self.assertEqual(restored, version)

    def test_empty_registry_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            snapshot = inspect_memory_policy_registry(root)
            self.assertFalse(root.exists())
            self.assertFalse(snapshot.registry_exists)
            self.assertEqual(snapshot.versions, ())
            self.assertFalse(snapshot.registry_modified)

    def test_registry_reads_versions_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policies = root / "policies"
            policies.mkdir()
            candidate = default_memory_policy_search_space().candidates[0]
            version = MemoryPolicyVersion(
                version_id="policy-v1", policy=candidate,
                status=MemoryPolicyLifecycleStatus.ACTIVE,
                created_at="2026-07-20T00:00:00+00:00",
                created_by="tester", source="test",
            )
            (policies / "policy_versions.jsonl").write_text(
                json.dumps(version.to_dict()) + "\n", encoding="utf-8"
            )
            (policies / "policy_state.json").write_text(
                json.dumps({
                    "active_policy_version_id": "policy-v1",
                    "pending_proposal_ids": ["proposal-v2"],
                }), encoding="utf-8"
            )
            snapshot = inspect_memory_policy_registry(root)
            self.assertEqual(snapshot.active_version, version)
            self.assertEqual(snapshot.pending_proposal_ids, ("proposal-v2",))
            self.assertFalse(snapshot.registry_modified)

    def test_registry_counts_malformed_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policies = root / "policies"
            policies.mkdir()
            (policies / "policy_versions.jsonl").write_text("not-json\n", encoding="utf-8")
            snapshot = inspect_memory_policy_registry(root)
            self.assertEqual(snapshot.malformed_record_count, 1)

    def test_preview_does_not_propose_or_activate(self) -> None:
        result = search_memory_policies()
        preview = preview_memory_policy_proposal(
            result, proposal_id="proposal-v1", created_by="tester",
            active_version_id="active-v0", created_at="2026-07-20T00:00:00+00:00",
        )
        self.assertEqual(preview.proposed_version.status, MemoryPolicyLifecycleStatus.PROPOSED)
        self.assertFalse(preview.policy_proposed)
        self.assertFalse(preview.policy_approved)
        self.assertFalse(preview.policy_activated)
        self.assertFalse(preview.registry_modified)
        self.assertTrue(preview.dry_run)

    def test_preview_rejects_empty_id(self) -> None:
        with self.assertRaises(ValueError):
            preview_memory_policy_proposal(
                search_memory_policies(), proposal_id="", created_by="tester"
            )

    def test_comparison_without_active_policy_requires_review(self) -> None:
        preview = preview_memory_policy_proposal(
            search_memory_policies(), proposal_id="proposal-v1",
            created_by="tester", created_at="2026-07-20T00:00:00+00:00",
        )
        comparison = compare_memory_policy_versions(None, preview.proposed_version)
        self.assertTrue(comparison.policy_changed)
        self.assertIsNone(comparison.combined_score_delta)
        self.assertEqual(comparison.recommendation, "manual_review_required")
        self.assertFalse(comparison.registry_modified)

    def test_comparison_calculates_metric_deltas(self) -> None:
        candidates = default_memory_policy_search_space().candidates
        baseline_metrics = MemoryPolicyMetrics(0.5, 0.5, 1.0, 0.5, 1.0, 0.0, 0.6)
        proposed_metrics = MemoryPolicyMetrics(0.7, 0.8, 1.0, 0.6, 1.0, 0.1, 0.8)
        current = MemoryPolicyVersion(
            "v1", candidates[0], MemoryPolicyLifecycleStatus.ACTIVE,
            "2026-07-20T00:00:00+00:00", "tester", "test", metrics=baseline_metrics,
        )
        proposed = MemoryPolicyVersion(
            "v2", candidates[-1], MemoryPolicyLifecycleStatus.PROPOSED,
            "2026-07-20T00:00:01+00:00", "tester", "automl", parent_version_id="v1",
            metrics=proposed_metrics,
        )
        comparison = compare_memory_policy_versions(current, proposed)
        self.assertAlmostEqual(comparison.combined_score_delta or 0.0, 0.2)
        self.assertIn("combined_score_improves", comparison.advantages)
        self.assertEqual(comparison.protected_memory_safety_delta, 0.0)

    def test_comparison_detects_identical_policy(self) -> None:
        candidate = default_memory_policy_search_space().candidates[0]
        current = MemoryPolicyVersion(
            "v1", candidate, MemoryPolicyLifecycleStatus.ACTIVE,
            "2026-07-20T00:00:00+00:00", "tester", "test",
        )
        proposed = MemoryPolicyVersion(
            "v2", candidate, MemoryPolicyLifecycleStatus.PROPOSED,
            "2026-07-20T00:00:01+00:00", "tester", "automl",
        )
        comparison = compare_memory_policy_versions(current, proposed)
        self.assertFalse(comparison.policy_changed)


if __name__ == "__main__":
    unittest.main()
