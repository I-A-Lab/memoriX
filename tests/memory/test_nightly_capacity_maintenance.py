"""Phase 2A5 elastic global Hot-Titan capacity: nightly capacity-maintenance tests.

Every test builds a fresh scratch runtime inside a TemporaryDirectory. No real
runtime data under the user profile is ever read or written, and no production
code is modified. Tiny Titan dims (d_model=16, hidden_dim=16) keep the tests
fast and deterministic (torch.manual_seed(42)).

Contract under test (final authority: the ENFORCED Phase 2A5 PRD contract in
memory/hot_site/titan_active_memory/elastic_capacity.py, memory/sync/nightly.py
and memory/gateway/capacity_control.py):

- run_nightly_capacity_maintenance(hot_site, *, policy=None,
  capacity_operations, run_reference, cold_archive_path=None,
  log_path=None) -> NightlyCapacityMaintenanceResult;
- NightlyCapacityMaintenanceResult.to_dict() has EXACTLY these 12 keys in
  order: capacity_before, capacity_after, active_before, active_after,
  automatic_soft_forgets, compaction_attempted, compaction_applied,
  shrink_attempted, shrink_applied, shrink_skipped_reason, consistency_ok,
  cold_site_modified;
- the nightly observes pressure with weights
  PressureWeights(usage_ratio=1.0, momentum=0.0, entropy=0.0, surprise=0.0,
  persistence=0.0), so memory_pressure == active / current_capacity and the
  default SoftPruningPolicy.minimum_pressure (0.70) is reachable at >= 70%
  usage under the default policy;
- automatic soft-forgets are applied by NIGHTLY_CAPACITY_REVIEWER ==
  "memorix_nightly_capacity" (forget log forgotten_by), and the forget reason
  contains the run reference; ElasticCapacityPolicy.max_automatic_deactivations
  is wired through apply_soft_pruning_plan;
- sequence is prune -> consistency gate -> compact -> shrink; a failed
  consistency gate blocks compaction and shrink (consistency_ok False,
  compaction_attempted False, shrink_attempted False, shrink_applied False,
  shrink_skipped_reason non-empty) and keeps capacity_after == capacity_before;
- restoration to the baseline happens only when
  active_after <= floor(baseline * 0.80) AND the consistency gate passed;
- when not expanded (current == baseline) the run is a no-op with every
  counter 0, capacity_after == capacity_before, consistency_ok False,
  shrink_attempted False and shrink_skipped_reason "";
- the cold archive stays byte-identical; the NightlyRunner latest status keeps
  'status': 'completed' and 'consolidation' and includes 'capacity_maintenance'.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from memory.data import MemoryStoragePaths, ValidatedMemory
from memory.gateway import MemoriXGateway
from memory.gateway.capacity_control import CapacityAdmissionError
from memory.gateway.capacity_operations import CapacityOperations
from memory.hot_site.titan_active_memory.elastic_capacity import (
    NIGHTLY_CAPACITY_REVIEWER,
    ElasticCapacityPolicy,
    NightlyCapacityMaintenanceResult,
    run_nightly_capacity_maintenance,
)
from memory.sync import snapshot_file
from memory.sync.nightly_runner import (
    EXIT_COMPLETED,
    NightlyRunner,
)

EXACT_RESULT_KEYS = [
    "capacity_before",
    "capacity_after",
    "active_before",
    "active_after",
    "automatic_soft_forgets",
    "compaction_attempted",
    "compaction_applied",
    "shrink_attempted",
    "shrink_applied",
    "shrink_skipped_reason",
    "consistency_ok",
    "cold_site_modified",
]

RUN_REFERENCE = "run_capacity_test_001"


class NightlyCapacityMaintenanceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        torch.manual_seed(42)
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.paths = MemoryStoragePaths.from_runtime_root(self.root)
        self.gateway = self.build_gateway(self.paths)

    def build_gateway(
        self,
        paths: MemoryStoragePaths,
        *,
        max_items: int = 50,
    ) -> MemoriXGateway:
        return MemoriXGateway(
            storage_paths=paths,
            titan_d_model=16,
            titan_hidden_dim=16,
            titan_max_items=max_items,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def validate_fresh(
        self,
        gateway: MemoriXGateway,
        index: int,
        **candidate_kwargs,
    ):
        content = (
            f"Nightly capacity fact number {index:03d} "
            "about the nightly quux."
        )
        candidate = gateway.propose_memory_candidate(
            content=content,
            reason="Nightly capacity test.",
            source_event_ids=(f"event_nightly_capacity_{index:03d}",),
            **candidate_kwargs,
        )
        return gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved nightly capacity test.",
        )

    def fill(
        self,
        gateway: MemoriXGateway,
        count: int,
        **candidate_kwargs,
    ) -> None:
        for index in range(1, count + 1):
            self.validate_fresh(gateway, index, **candidate_kwargs)

    def expand_to(self, gateway: MemoriXGateway) -> None:
        """Fill the baseline (50) and validate the 51st memory so the
        elastic capacity reaches 63."""
        self.fill(gateway, 50)
        try:
            self.validate_fresh(gateway, 51)
        except CapacityAdmissionError:
            self.skipTest(
                "admission-time capacity expansion is not "
                "implemented yet (the 51st validation is "
                "rejected)."
            )

    def seed_direct(
        self,
        gateway: MemoriXGateway,
        count: int,
        *,
        prefix: str,
        metadata: dict,
        created_at: str = "2020-01-01T00:00:00+00:00",
    ):
        stored = []
        for index in range(1, count + 1):
            memory = ValidatedMemory(
                memory_id=f"{prefix}_{index:03d}",
                content=(
                    f"Direct capacity seed {prefix} number "
                    f"{index:03d} about the nightly quux."
                ),
                source_candidate_id=f"candidate_{prefix}_{index:03d}",
                created_at=created_at,
                validated_at=created_at,
                active=True,
                version=1,
                metadata=dict(metadata),
            )
            gateway._hot_site.store_validated(
                memory,
                validated_by="human_reviewer",
                validation_reason="Direct nightly seed.",
            )
            stored.append(memory)
        return stored

    def low_retention_metadata(self) -> dict:
        return {
            "importance": 0.2,
            "access_count": 0,
            "retrieval_score": 0.0,
            "pinned": False,
            "human_validated": False,
        }

    def capacity_status(self) -> dict:
        return self.gateway._hot_site.capacity_status()

    def active_count(self) -> int:
        return len(
            self.gateway._hot_site.list_memories(active_only=True)
        )

    def active_ids(self) -> set:
        return {
            memory.memory_id
            for memory in self.gateway._hot_site.list_memories(
                active_only=True
            )
        }

    def forget_log_records(self) -> list:
        path = Path(self.paths.titan_metadata).with_name(
            "titan_forget_log.jsonl"
        )
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def run_maintenance(self, *, policy=None, run_reference=RUN_REFERENCE):
        """Run the real maintenance function against the live hot site.

        The enforced signature carries the growth policy, the capacity
        operations journal, the run reference and the cold archive path. The
        automatic soft-forget reviewer is the NIGHTLY_CAPACITY_REVIEWER
        constant inside the maintenance function.
        """
        return run_nightly_capacity_maintenance(
            self.gateway._hot_site,
            policy=policy,
            capacity_operations=CapacityOperations(
                lock_path=self.paths.capacity_lock,
                events_path=self.paths.capacity_events,
                latest_path=self.paths.capacity_latest,
            ),
            run_reference=run_reference,
            cold_archive_path=self.paths.cold_archive_events,
        )


class NightlyCapacityMaintenancePruningTests(
    NightlyCapacityMaintenanceTestCase
):
    def test_noop_when_not_expanded(self) -> None:
        """current == baseline -> a no-op result with every counter 0."""
        self.fill(self.gateway, 30)
        self.assertEqual(self.capacity_status()["current_capacity"], 50)

        result = self.run_maintenance()

        self.assertIsInstance(result, NightlyCapacityMaintenanceResult)
        self.assertEqual(result.automatic_soft_forgets, 0)
        self.assertEqual(result.capacity_before, 50)
        self.assertEqual(
            result.capacity_after,
            result.capacity_before,
            "a non-expanded hot site must keep its capacity",
        )
        self.assertEqual(result.active_before, 30)
        self.assertEqual(result.active_after, 30)
        self.assertFalse(result.consistency_ok)
        self.assertFalse(result.compaction_attempted)
        self.assertFalse(result.compaction_applied)
        self.assertFalse(result.shrink_attempted)
        self.assertFalse(result.shrink_applied)
        self.assertEqual(
            result.shrink_skipped_reason,
            "",
            "a no-op run must not report a shrink skip reason",
        )
        self.assertFalse(result.cold_site_modified)

    def test_default_policy_pruning_is_reachable_and_respects_protections(
        self,
    ) -> None:
        """At >= 70% usage the default policy prunes low-retention seeds
        only; pinned, high-importance, high-access and recent memories are
        kept; the forget log carries the enforced reviewer and run
        reference."""
        self.expand_to(self.gateway)

        low_retention = self.seed_direct(
            self.gateway,
            10,
            prefix="low_retention",
            metadata=self.low_retention_metadata(),
        )
        pinned = self.seed_direct(
            self.gateway,
            1,
            prefix="pinned_seed",
            metadata={
                "importance": 0.2,
                "access_count": 0,
                "retrieval_score": 0.0,
                "pinned": True,
                "human_validated": True,
            },
        )
        high_importance = self.seed_direct(
            self.gateway,
            1,
            prefix="important_seed",
            metadata={
                "importance": 0.95,
                "access_count": 0,
                "retrieval_score": 0.0,
                "pinned": False,
                "human_validated": True,
            },
        )
        high_access = self.seed_direct(
            self.gateway,
            1,
            prefix="accessed_seed",
            metadata={
                "importance": 0.2,
                "access_count": 999,
                "retrieval_score": 0.0,
                "pinned": False,
                "human_validated": True,
            },
        )
        recent = self.seed_direct(
            self.gateway,
            1,
            prefix="recent_seed",
            metadata={
                "importance": 0.2,
                "access_count": 0,
                "retrieval_score": 0.0,
                "pinned": False,
                "human_validated": True,
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # 65 active, capacity 79 -> usage 65/79 = 0.82 >= 0.70.
        self.assertEqual(self.active_count(), 65)
        self.assertEqual(self.capacity_status()["current_capacity"], 79)

        result = self.run_maintenance()

        protected_ids = {
            *(memory.memory_id for memory in pinned),
            *(memory.memory_id for memory in high_importance),
            *(memory.memory_id for memory in high_access),
            *(memory.memory_id for memory in recent),
        }
        low_ids = {memory.memory_id for memory in low_retention}
        active_ids = self.active_ids()

        self.assertGreaterEqual(
            result.automatic_soft_forgets,
            1,
            "usage 0.82 >= minimum_pressure 0.70 must prune under "
            "the default policy",
        )
        self.assertEqual(
            result.automatic_soft_forgets,
            10,
            "exactly the 10 unprotected low-retention seeds are "
            "soft-forgotten",
        )
        self.assertTrue(
            protected_ids.issubset(active_ids),
            "pinned, high-importance, high-access and recent "
            "memories must never be deactivated",
        )
        self.assertEqual(
            low_ids & active_ids,
            set(),
            "every low-retention unprotected memory must be "
            "soft-forgotten",
        )
        self.assertEqual(result.active_after, 55)

        records = self.forget_log_records()
        self.assertEqual(
            len(records),
            result.automatic_soft_forgets,
            "every automatic soft-forget must be logged",
        )
        self.assertTrue(
            all(
                record.get("forgotten_by")
                == NIGHTLY_CAPACITY_REVIEWER
                == "memorix_nightly_capacity"
                for record in records
            ),
            "automatic soft-forgets must use the enforced reviewer",
        )
        self.assertTrue(
            all(
                RUN_REFERENCE in record.get("forget_reason", "")
                for record in records
            ),
            "every automatic soft-forget must reference the run",
        )

        self.assertTrue(result.consistency_ok)
        self.assertTrue(result.compaction_attempted)
        self.assertTrue(result.compaction_applied)
        self.assertFalse(result.shrink_attempted)
        self.assertEqual(
            result.capacity_after,
            79,
            "55 active > floor(50 * 0.8) == 40 so the elastic "
            "capacity is kept",
        )

    def test_max_automatic_deactivations_capped(self) -> None:
        """ElasticCapacityPolicy(max_automatic_deactivations=1) caps the
        nightly soft-forgets at 1."""
        self.expand_to(self.gateway)
        self.seed_direct(
            self.gateway,
            5,
            prefix="capped_low",
            metadata=self.low_retention_metadata(),
        )
        # 56 active, capacity 63 -> usage 56/63 = 0.89 >= 0.70.
        self.assertEqual(self.active_count(), 56)

        result = self.run_maintenance(
            policy=ElasticCapacityPolicy(
                max_automatic_deactivations=1
            )
        )

        self.assertEqual(
            result.automatic_soft_forgets,
            1,
            "max_automatic_deactivations=1 must cap the forgets",
        )
        self.assertEqual(result.active_after, 55)
        self.assertEqual(
            len(self.forget_log_records()),
            1,
        )

    def test_consistency_failure_blocks_shrink(self) -> None:
        """An intentionally inconsistent hot site blocks compaction and
        shrink; capacity and the cold archive stay unchanged."""
        self.expand_to(self.gateway)
        self.assertEqual(self.capacity_status()["current_capacity"], 63)

        # Deactivate a Titan item directly (bypassing metadata) so an active
        # metadata record has no live Titan item: a real inconsistency.
        backend = self.gateway._hot_site._backend
        item = backend.memory.active_items[0]
        backend.memory.deactivate_ids(
            [int(item.id)],
            reason="intentional inconsistency",
        )
        gate = backend.consistency_gate()
        self.assertFalse(gate.passed)

        cold_before = snapshot_file(self.paths.cold_archive_events)

        result = self.run_maintenance()

        self.assertFalse(result.consistency_ok)
        self.assertFalse(result.compaction_attempted)
        self.assertFalse(result.compaction_applied)
        self.assertFalse(result.shrink_attempted)
        self.assertFalse(result.shrink_applied)
        self.assertTrue(
            result.shrink_skipped_reason,
            "a failed consistency gate must explain the skip",
        )
        self.assertEqual(
            result.capacity_after,
            result.capacity_before,
            "a failed consistency gate must keep the capacity",
        )
        self.assertEqual(result.capacity_after, 63)
        self.assertEqual(result.automatic_soft_forgets, 0)

        cold_after = snapshot_file(self.paths.cold_archive_events)
        self.assertEqual(cold_after, cold_before)
        self.assertFalse(result.cold_site_modified)

    def test_restoration_at_or_below_80_percent(self) -> None:
        """Expanded 63 with active 40 (== floor(50 * 0.8)) after compaction
        restores the baseline 50."""
        self.expand_to(self.gateway)
        self.assertEqual(self.capacity_status()["current_capacity"], 63)

        memories = self.gateway._hot_site.list_memories(
            active_only=True
        )
        for memory in memories[:11]:
            self.gateway.forget_memory(
                memory.memory_id,
                validated_by="human_reviewer",
                reason="Restore test deactivation.",
            )
        self.assertEqual(self.active_count(), 40)

        result = self.run_maintenance()

        self.assertEqual(result.automatic_soft_forgets, 0)
        self.assertTrue(result.consistency_ok)
        self.assertTrue(result.compaction_attempted)
        self.assertTrue(
            result.compaction_applied,
            "the 11 inactive memories must be compacted",
        )
        self.assertTrue(
            result.shrink_attempted,
            "active 40 <= floor(50 * 0.8) == 40 so the shrink "
            "must be attempted",
        )
        self.assertTrue(
            result.shrink_applied,
            "active 40 fits the headroom so the baseline must be "
            "restored",
        )
        self.assertEqual(result.active_after, 40)
        self.assertEqual(
            result.capacity_after,
            50,
            "the current capacity must return to the baseline 50",
        )
        status = self.capacity_status()
        self.assertEqual(status["current_capacity"], 50)
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertFalse(status["expansion_active"])

    def test_no_restoration_above_80_percent(self) -> None:
        """Expanded 63 with active 51 (> floor(50 * 0.8) == 40) does not
        restore; the skip reason mentions the headroom rule."""
        self.expand_to(self.gateway)
        self.assertEqual(self.capacity_status()["current_capacity"], 63)
        self.assertEqual(self.active_count(), 51)

        result = self.run_maintenance()

        self.assertEqual(result.automatic_soft_forgets, 0)
        self.assertTrue(result.consistency_ok)
        self.assertFalse(result.shrink_attempted)
        self.assertFalse(result.shrink_applied)
        self.assertTrue(
            result.shrink_skipped_reason,
            "active 51 > floor(50 * 0.8) must explain the skip",
        )
        self.assertIn(
            "headroom",
            result.shrink_skipped_reason.lower(),
            "the skip reason must mention the headroom rule",
        )
        self.assertEqual(
            result.capacity_after,
            63,
            "active 51 > floor(50 * 0.8) == 40 so the elastic "
            "capacity is kept",
        )


class NightlyCapacityMaintenanceReportTests(
    NightlyCapacityMaintenanceTestCase
):
    def test_report_has_exactly_12_keys(self) -> None:
        """to_dict() exposes exactly the enforced 12 keys in order."""
        self.expand_to(self.gateway)

        result = self.run_maintenance()

        self.assertIsInstance(result, NightlyCapacityMaintenanceResult)
        payload = result.to_dict()
        self.assertEqual(
            set(payload),
            set(EXACT_RESULT_KEYS),
            "to_dict() must expose exactly the 12 enforced keys "
            "and no extras",
        )
        self.assertEqual(
            list(payload),
            EXACT_RESULT_KEYS,
            "to_dict() must preserve the enforced key order",
        )
        self.assertEqual(len(payload), 12)

    def test_cold_archive_unchanged(self) -> None:
        """The cold archive stays byte-identical through maintenance."""
        self.gateway.record_memory_event(
            content="Nightly capacity cold-site seed event.",
            event_type="capacity_nightly_seed",
            source="unit_test",
            importance=0.5,
        )
        self.expand_to(self.gateway)

        cold_before = snapshot_file(self.paths.cold_archive_events)
        result = self.run_maintenance()

        cold_after = snapshot_file(self.paths.cold_archive_events)
        self.assertEqual(cold_after, cold_before)
        self.assertFalse(result.cold_site_modified)


class _NightlyReport:
    """Stand-in for the nightly report used by the NightlyRunner."""

    capacity_maintenance = {
        "capacity_before": 63,
        "capacity_after": 50,
        "active_before": 40,
        "active_after": 40,
        "automatic_soft_forgets": 0,
        "compaction_attempted": True,
        "compaction_applied": True,
        "shrink_attempted": True,
        "shrink_applied": True,
        "shrink_skipped_reason": "",
        "consistency_ok": True,
        "cold_site_modified": False,
    }

    def to_dict(self) -> dict:
        return {
            "status": "completed",
            "consolidation": {"candidates_created": 0},
            "capacity_maintenance": self.capacity_maintenance,
        }


class NightlyCapacityMaintenanceRunnerTests(unittest.TestCase):
    def test_nightly_runner_status_includes_capacity_maintenance(
        self,
    ) -> None:
        """The latest status keeps 'status': 'completed' and
        'consolidation' and includes 'capacity_maintenance'."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"
            with patch(
                "memory.sync.nightly_runner.MemoriXGateway"
            ) as gateway:
                gateway.return_value.run_nightly_consolidation.return_value = (
                    _NightlyReport()
                )
                result = NightlyRunner(root).run()

            paths = MemoryStoragePaths.from_runtime_root(root)
            self.assertEqual(result.exit_code, EXIT_COMPLETED)
            latest = json.loads(
                paths.nightly_latest.read_text(encoding="utf-8")
            )
            self.assertEqual(latest["status"], "completed")
            self.assertIn(
                "consolidation",
                latest,
                "the latest status must keep consolidation",
            )
            self.assertIn(
                "capacity_maintenance",
                latest,
                "the latest status must include capacity_maintenance",
            )
            self.assertEqual(
                latest["capacity_maintenance"],
                _NightlyReport.capacity_maintenance,
            )


if __name__ == "__main__":
    unittest.main()
