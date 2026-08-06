from __future__ import annotations

import unittest
from types import SimpleNamespace

from memory.benchmark.tenant_contradiction_audit import (
    TenantAuditRequest,
    _aggregate,
    _scope,
)


class TenantContradictionAuditTests(unittest.TestCase):
    def test_quick_profile(self):
        request = TenantAuditRequest(profile="quick").resolved()
        self.assertEqual(request.seeds, (101, 202))
        self.assertEqual(request.user_count, 4)
        self.assertEqual(request.project_count, 3)
        self.assertEqual(request.distractor_count, 50)

    def test_invalid_user_count(self):
        with self.assertRaises(ValueError):
            TenantAuditRequest(user_count=2).resolved()

    def test_scope_from_metadata(self):
        match = SimpleNamespace(metadata={"project_id": "P", "user_id": "U"})
        self.assertEqual(_scope(match), ("P", "U"))

    def test_aggregate_separates_gates(self):
        check_type = SimpleNamespace
        checks = [
            check_type(
                category="storage",
                scenario="storage",
                passed=True,
                duration_ms=1.0,
            ),
            check_type(
                category="retrieval",
                scenario="retrieval",
                passed=False,
                duration_ms=1.5,
            ),
            check_type(
                category="isolation",
                scenario="isolation",
                passed=False,
                duration_ms=2.0,
            ),
            check_type(
                category="diagnostic",
                scenario="diagnostic",
                passed=True,
                duration_ms=3.0,
            ),
        ]
        aggregate = _aggregate(checks)
        self.assertTrue(aggregate["storage_lifecycle_gate_passed"])
        self.assertFalse(aggregate["retrieval_namespace_gate_passed"])
        self.assertFalse(aggregate["tenant_isolation_gate_passed"])
        self.assertEqual(aggregate["retrieval_warning_count"], 1)
        self.assertEqual(aggregate["isolation_warning_count"], 1)


if __name__ == "__main__":
    unittest.main()
