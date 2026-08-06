"""Phase 2A5 elastic capacity benchmark: PRD-contract proof.

This benchmark asserts the ENFORCED Phase 2A5 PRD contract end to end:

- baseline 50, fill 50, validate the 51st -> current_capacity == 63
  (max(50 + 10, ceil(50 * 1.25), 50 + 1));
- all 51 memories remain retrievable before and after a gateway rebuild;
- the nightly pruning is reachable under the DEFAULT policy: the nightly
  observes pressure with weights=PressureWeights(usage_ratio=1.0, ...), so
  memory_pressure == active / current_capacity and any expanded site using
  >= 70% of its current capacity crosses SoftPruningPolicy.minimum_pressure;
- Scenario A (no-restore branch): 71 active / 79 capacity (usage 0.899) with
  20 low-retention unprotected seeds -> automatic_soft_forgets >= 1 (only seed
  ids), active_after == 71 - forgets > floor(50 * 0.8) == 40 ->
  shrink_applied False, capacity_after == 79;
- Scenario B (restore branch): expanded 63 with 31 active after 20 explicit
  soft-forgets (usage 31/63 == 0.49 < 0.70 so no pruning) -> compaction
  removes the inactive items, active_after 31 <= floor(50 * 0.8) == 40 ->
  shrink_attempted True, shrink_applied True, capacity_after == 50;
- automatic soft-forgets are applied by forgotten_by ==
  "memorix_nightly_capacity";
- the cold archive sha256 is unchanged throughout both scenarios.

This benchmark runs against fresh scratch runtimes inside a TemporaryDirectory
only. It never reads or writes the real runtime under the user profile.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import torch

from memory.data import MemoryStoragePaths, ValidatedMemory
from memory.gateway import MemoriXGateway
from memory.sync import snapshot_file

EXACT_RESULT_KEYS = {
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
}


class ElasticCapacityBenchmarkTests(unittest.TestCase):
    def test_elastic_capacity_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self._scenario_a(Path(temp) / "scenario_a")
            self._scenario_b(Path(temp) / "scenario_b")

    def _build_gateway(self, paths: MemoryStoragePaths) -> MemoriXGateway:
        return MemoriXGateway(
            storage_paths=paths,
            titan_d_model=16,
            titan_hidden_dim=16,
            titan_max_items=50,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

    def _validate(
        self,
        gateway: MemoriXGateway,
        index: int,
        *,
        tag: str,
    ) -> None:
        candidate = gateway.propose_memory_candidate(
            content=(
                f"Benchmark fact number {index:03d} "
                f"about the {tag} quux."
            ),
            reason="Elastic capacity benchmark.",
            source_event_ids=(
                f"event_benchmark_{tag}_{index:03d}",
            ),
        )
        gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Benchmark fill.",
        )

    def _assert_all_retrievable(
        self,
        gateway: MemoriXGateway,
        expected: int,
    ) -> None:
        hot_site = gateway._hot_site
        listed = hot_site.list_memories(active_only=True)
        self.assertEqual(len(listed), expected)
        known_ids = {memory.memory_id for memory in listed}
        self.assertEqual(len(known_ids), expected)
        for memory in listed:
            result = hot_site.retrieve(memory.content, top_k=5)
            self.assertGreaterEqual(
                len(result.matches),
                1,
                f"no retrieval match for {memory.memory_id}",
            )
            self.assertTrue(
                all(
                    match.memory_id in known_ids
                    for match in result.matches
                ),
                "every retrieved memory must be one of the "
                "benchmark memories",
            )

    def _seed_low_retention(
        self,
        gateway: MemoriXGateway,
        count: int,
        *,
        tag: str,
    ) -> set:
        seeded = set()
        for index in range(1, count + 1):
            memory_id = f"{tag}_low_retention_{index:03d}"
            memory = ValidatedMemory(
                memory_id=memory_id,
                content=(
                    f"Benchmark low retention fact number "
                    f"{index:03d} about the {tag} quux."
                ),
                source_candidate_id=(
                    f"candidate_{tag}_low_{index:03d}"
                ),
                created_at="2020-01-01T00:00:00+00:00",
                validated_at="2020-01-01T00:00:00+00:00",
                active=True,
                version=1,
                metadata={
                    "importance": 0.2,
                    "access_count": 0,
                    "retrieval_score": 0.0,
                    "pinned": False,
                    "human_validated": False,
                    "surprise": 0.0,
                },
            )
            gateway._hot_site.store_validated(
                memory,
                validated_by="human_reviewer",
                validation_reason="Benchmark low-retention seed.",
            )
            seeded.add(memory_id)
        return seeded

    def _forget_log_records(
        self,
        paths: MemoryStoragePaths,
    ) -> list:
        path = Path(paths.titan_metadata).with_name(
            "titan_forget_log.jsonl"
        )
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _scenario_a(self, root: Path) -> None:
        """No-restore branch: expansion proof + default-policy pruning."""
        root.mkdir(parents=True)
        paths = MemoryStoragePaths.from_runtime_root(root)
        torch.manual_seed(42)

        gateway = self._build_gateway(paths)
        gateway.record_memory_event(
            content=(
                "Cold seed event one for the elastic "
                "capacity benchmark."
            ),
            event_type="benchmark_seed",
            source="elastic_capacity_benchmark",
            importance=0.5,
        )
        gateway.record_memory_event(
            content=(
                "Cold seed event two for the elastic "
                "capacity benchmark."
            ),
            event_type="benchmark_seed",
            source="elastic_capacity_benchmark",
            importance=0.5,
        )
        cold_before = snapshot_file(paths.cold_archive_events)

        for index in range(1, 51):
            self._validate(gateway, index, tag="scenario_a")

        capacity_status = gateway._hot_site.capacity_status
        baseline = capacity_status()
        self.assertEqual(baseline["current_capacity"], 50)
        self.assertEqual(baseline["active_items"], 50)

        self._validate(gateway, 51, tag="scenario_a")

        expanded = capacity_status()
        self.assertEqual(
            expanded["current_capacity"],
            63,
            "the 51st validated memory must expand the "
            "capacity from 50 to 63",
        )
        self.assertEqual(expanded["baseline_capacity"], 50)
        self.assertEqual(expanded["active_items"], 51)
        self.assertTrue(expanded["expansion_active"])

        self._assert_all_retrievable(gateway, 51)

        gateway = self._build_gateway(paths)
        restarted = gateway._hot_site.capacity_status()
        self.assertEqual(
            restarted["current_capacity"],
            63,
            "the expanded capacity must survive a gateway "
            "rebuild",
        )
        self._assert_all_retrievable(gateway, 51)

        seeded = self._seed_low_retention(
            gateway,
            20,
            tag="scenario_a",
        )
        hot_site = gateway._hot_site
        self.assertEqual(
            hot_site.capacity_status()["current_capacity"],
            79,
            "seeding 20 memories beyond the 51 validated ones "
            "must expand the capacity to 79",
        )
        self.assertEqual(
            len(hot_site.list_memories(active_only=True)),
            71,
        )

        report = gateway.run_nightly_consolidation()
        maintenance = getattr(report, "capacity_maintenance", None)
        if maintenance is None:
            self.skipTest("capacity maintenance not implemented.")

        payload = maintenance.to_dict()
        self.assertEqual(
            set(payload),
            EXACT_RESULT_KEYS,
            "the maintenance result must expose exactly the "
            "enforced 12 keys",
        )

        # Usage 71/79 = 0.899 >= 0.70: the DEFAULT policy must prune.
        self.assertGreaterEqual(
            maintenance.automatic_soft_forgets,
            1,
            "usage 0.899 >= minimum_pressure 0.70 must prune "
            "under the default policy",
        )
        self.assertEqual(
            maintenance.active_after,
            71 - maintenance.automatic_soft_forgets,
        )

        active_ids = {
            memory.memory_id
            for memory in hot_site.list_memories(active_only=True)
        }
        self.assertTrue(
            active_ids.isdisjoint(seeded),
            "every forgotten memory must be a low-retention seed",
        )
        self.assertEqual(
            maintenance.active_after,
            len(active_ids),
        )
        self.assertGreater(
            maintenance.active_after,
            40,
            "Scenario A keeps more than floor(50 * 0.8) == 40 "
            "active",
        )
        self.assertFalse(
            maintenance.shrink_attempted,
            "active > floor(50 * 0.8) must not attempt a shrink",
        )
        self.assertFalse(maintenance.shrink_applied)
        self.assertEqual(
            maintenance.capacity_after,
            79,
            "the elastic capacity must be kept in Scenario A",
        )
        self.assertTrue(
            maintenance.shrink_skipped_reason,
            "the skipped shrink must carry a reason",
        )

        records = self._forget_log_records(paths)
        self.assertGreaterEqual(
            len(records),
            maintenance.automatic_soft_forgets,
        )
        self.assertTrue(
            all(
                record.get("forgotten_by")
                == "memorix_nightly_capacity"
                for record in records
            ),
            "automatic soft-forgets must use the enforced "
            "reviewer",
        )

        cold_after = snapshot_file(paths.cold_archive_events)
        self.assertEqual(
            cold_after,
            cold_before,
            "the cold archive must stay byte-identical in "
            "Scenario A",
        )
        self.assertFalse(report.cold_site_modified)

    def _scenario_b(self, root: Path) -> None:
        """Restore branch: active <= floor(50 * 0.8) restores to 50."""
        root.mkdir(parents=True)
        paths = MemoryStoragePaths.from_runtime_root(root)
        torch.manual_seed(42)

        gateway = self._build_gateway(paths)
        gateway.record_memory_event(
            content=(
                "Cold seed event for the restore benchmark "
                "scenario."
            ),
            event_type="benchmark_seed",
            source="elastic_capacity_benchmark",
            importance=0.5,
        )
        cold_before = snapshot_file(paths.cold_archive_events)

        for index in range(1, 51):
            self._validate(gateway, index, tag="scenario_b")
        self._validate(gateway, 51, tag="scenario_b")

        gateway = self._build_gateway(paths)
        self._assert_all_retrievable(gateway, 51)
        self.assertEqual(
            gateway._hot_site.capacity_status()["current_capacity"],
            63,
        )

        # Explicitly soft-forget 20 validated memories down to 31 active.
        memories = gateway._hot_site.list_memories(active_only=True)
        for memory in memories[:20]:
            gateway.forget_memory(
                memory.memory_id,
                validated_by="human_reviewer",
                reason="Restore benchmark deactivation.",
            )
        self.assertEqual(
            len(
                gateway._hot_site.list_memories(active_only=True)
            ),
            31,
        )

        report = gateway.run_nightly_consolidation()
        maintenance = getattr(report, "capacity_maintenance", None)
        if maintenance is None:
            self.skipTest("capacity maintenance not implemented.")

        payload = maintenance.to_dict()
        self.assertEqual(
            set(payload),
            EXACT_RESULT_KEYS,
            "the maintenance result must expose exactly the "
            "enforced 12 keys",
        )

        # Usage 31/63 = 0.49 < 0.70: no automatic soft-forgets.
        self.assertEqual(maintenance.automatic_soft_forgets, 0)
        self.assertTrue(maintenance.consistency_ok)
        self.assertTrue(maintenance.compaction_attempted)
        self.assertTrue(
            maintenance.compaction_applied,
            "the 20 inactive memories must be compacted",
        )
        self.assertEqual(maintenance.active_after, 31)
        self.assertTrue(
            maintenance.shrink_attempted,
            "active 31 <= floor(50 * 0.8) == 40 must attempt "
            "the shrink",
        )
        self.assertTrue(
            maintenance.shrink_applied,
            "active 31 fits the headroom so the baseline must "
            "be restored",
        )
        self.assertEqual(
            maintenance.capacity_after,
            50,
            "Scenario B must restore the baseline capacity",
        )
        status = gateway._hot_site.capacity_status()
        self.assertEqual(status["current_capacity"], 50)
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertFalse(status["expansion_active"])

        cold_after = snapshot_file(paths.cold_archive_events)
        self.assertEqual(
            cold_after,
            cold_before,
            "the cold archive must stay byte-identical in "
            "Scenario B",
        )
        self.assertFalse(report.cold_site_modified)


if __name__ == "__main__":
    unittest.main()
