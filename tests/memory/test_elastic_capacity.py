"""Phase 2A5 elastic global Hot-Titan capacity: admission-time expansion tests.

Every test builds a fresh scratch runtime inside a TemporaryDirectory. No real
runtime data under the user profile is ever read or written, and no production
code is modified. Tiny Titan dims (d_model=16, hidden_dim=16) keep the tests
fast and deterministic (torch.manual_seed(42)).

Contract under test (final authority: the ENFORCED Phase 2A5 PRD contract):
- expansion formula: new_capacity = max(current + minimum_growth,
  ceil(current * growth_factor), item_count + required_slots) with
  minimum_growth=10 and growth_factor=1.25 by default; applied only when
  item_count + required_slots exceeds the current capacity; never evicts;
- ElasticCapacityPolicy fields: minimum_growth=10, growth_factor=1.25,
  baseline_headroom_ratio=0.80, max_automatic_deactivations=200; validate()
  raises ValueError on minimum_growth < 1, growth_factor <= 1.0,
  headroom_ratio outside (0, 1], max_automatic_deactivations < 1;
- NIGHTLY_CAPACITY_REVIEWER == "memorix_nightly_capacity";
- should_restore_baseline(active_count, *, baseline_capacity,
  headroom_ratio=0.80) -> True only when
  active_count <= math.floor(baseline_capacity * headroom_ratio);
- hot_site.capacity_status() exposes exactly {baseline_capacity,
  current_capacity, expansion_active, available_slots, usage_ratio,
  active_items, inactive_items, total_items};
  hot_site.ensure_capacity_for(required_slots) -> int;
- baseline 50, fill 50, validate the 51st -> current_capacity == 63;
- MemoryValidationService validates a candidate only after a successful
  admission-time expansion guarded by CapacityOperations.mutation_lock.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from memory.data import (
    CandidateStatus,
    MemoryStoragePaths,
    ValidatedMemory,
)
from memory.gateway import MemoriXGateway
from memory.gateway.capacity_control import (
    CapacityAdmissionError,
)
from memory.gateway.capacity_operations import (
    CapacityOperationLockedError,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)
from memory.hot_site.titan_active_memory.titan_model import (
    split_memory_units,
)

try:
    from memory.hot_site.titan_active_memory import (
        elastic_capacity as elastic_capacity_module,
    )

    compute_expanded_capacity = (
        elastic_capacity_module.compute_expanded_capacity
    )
    should_restore_baseline = (
        elastic_capacity_module.should_restore_baseline
    )
    ElasticCapacityPolicy = (
        elastic_capacity_module.ElasticCapacityPolicy
    )
    NIGHTLY_CAPACITY_REVIEWER = getattr(
        elastic_capacity_module,
        "NIGHTLY_CAPACITY_REVIEWER",
        None,
    )
    _ELASTIC_IMPORTED = True
except ImportError:  # dev_branch has not landed yet: skip gracefully
    elastic_capacity_module = None
    compute_expanded_capacity = None
    should_restore_baseline = None
    ElasticCapacityPolicy = None
    NIGHTLY_CAPACITY_REVIEWER = None
    _ELASTIC_IMPORTED = False


class ElasticCapacityTestCase(unittest.TestCase):
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
            f"Elastic capacity fact number {index:03d} "
            "about the alpha quux."
        )
        candidate = gateway.propose_memory_candidate(
            content=content,
            reason="Elastic capacity test.",
            source_event_ids=(f"event_elastic_{index:03d}",),
            **candidate_kwargs,
        )
        return gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="human_reviewer",
            validation_reason="Approved by capacity test.",
        )

    def validate_expansion(
        self,
        gateway: MemoriXGateway,
    ):
        """Validate the memory that exceeds the baseline capacity."""
        return self.validate_fresh(gateway, 51)

    def fill(
        self,
        gateway: MemoriXGateway,
        count: int,
        **candidate_kwargs,
    ) -> None:
        for index in range(1, count + 1):
            self.validate_fresh(gateway, index, **candidate_kwargs)

    def hot_site(self) -> HotSiteTitanMemory:
        return self.gateway._hot_site

    def capacity_status(self) -> dict:
        return self.hot_site().capacity_status()

    def ensure_capacity(self):
        hot_site = self.hot_site()
        ensure = getattr(hot_site, "ensure_capacity_for", None)
        if ensure is None:
            ensure = getattr(
                hot_site,
                "ensure_expanded_capacity",
                None,
            )
        if ensure is None:
            self.skipTest(
                "hot_site.ensure_capacity_for is not implemented yet."
            )
        return ensure

    def metadata_line_count(self) -> int:
        path = self.paths.titan_metadata
        if not path.exists():
            return 0
        return len(
            [
                line
                for line in path.read_text(
                    encoding="utf-8"
                ).splitlines()
                if line.strip()
            ]
        )


class ElasticCapacityOldStateTests(ElasticCapacityTestCase):
    def test_old_state_load_compat(self) -> None:
        """A .pt payload without elastic capacity keys reloads with the
        constructor baseline and current_capacity raised to the item count."""
        hot_site = self.hot_site()
        for index in range(1, 61):
            memory = ValidatedMemory(
                memory_id=f"memory_legacy_{index:03d}",
                content=(
                    f"Legacy capacity fact number {index:03d} "
                    "about the echo quux."
                ),
                source_candidate_id=(
                    f"candidate_legacy_{index:03d}"
                ),
                created_at="2025-01-01T00:00:00+00:00",
                validated_at="2025-01-01T00:00:00+00:00",
                active=True,
                version=1,
                metadata={"importance": 0.5},
            )
            hot_site.store_validated(
                memory,
                validated_by="human_reviewer",
                validation_reason="Legacy state seed.",
            )

        # Simulate a save produced before elastic capacity existed: strip
        # every capacity key from the payload on disk.
        neural_path = self.paths.titan_neural_state
        payload = torch.load(neural_path, map_location="cpu")
        for key in (
            "baseline_capacity",
            "current_capacity",
            "max_items",
            "capacity_expansion_active",
        ):
            payload.pop(key, None)
        torch.save(payload, neural_path)

        reloaded = self.build_gateway(self.paths)
        backend = reloaded._hot_site._backend

        self.assertEqual(backend.baseline_capacity, 50)
        self.assertEqual(
            backend.current_capacity,
            60,
            "legacy payloads must reload with capacity raised to "
            "the persisted item count",
        )
        self.assertEqual(
            len(reloaded._hot_site.list_memories()),
            60,
        )


class ElasticCapacityExpansionTests(ElasticCapacityTestCase):
    def test_expansion_at_real_full_capacity(self) -> None:
        """Baseline 50, fill 50, validating the 51st lands on exactly 63."""
        self.fill(self.gateway, 50)
        status = self.capacity_status()
        self.assertEqual(status["current_capacity"], 50)
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertFalse(status["expansion_active"])

        validated = self.validate_expansion(self.gateway)

        self.assertTrue(validated.memory_id)
        status = self.capacity_status()
        self.assertEqual(
            status["current_capacity"],
            63,
            "max(50 + 10, ceil(50 * 1.25), 50 + 1) == 63",
        )
        self.assertTrue(status["expansion_active"])
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertEqual(
            len(self.hot_site().list_memories(active_only=True)),
            51,
        )

    def test_expansion_persists_across_restart(self) -> None:
        """A rebuilt gateway over the same scratch paths keeps 63/50."""
        self.fill(self.gateway, 50)
        self.validate_expansion(self.gateway)
        self.assertEqual(self.capacity_status()["current_capacity"], 63)

        self.gateway = self.build_gateway(self.paths)

        status = self.capacity_status()
        self.assertEqual(status["current_capacity"], 63)
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertTrue(status["expansion_active"])
        self.assertEqual(
            len(self.hot_site().list_memories(active_only=True)),
            51,
        )

    def test_all_old_and_new_memories_retrievable(self) -> None:
        """After expansion + restart all 51 memories are retrievable."""
        self.fill(self.gateway, 50)
        self.validate_expansion(self.gateway)
        self.gateway = self.build_gateway(self.paths)

        hot_site = self.hot_site()
        listed = hot_site.list_memories(active_only=True)
        known_ids = {memory.memory_id for memory in listed}

        self.assertEqual(len(listed), 51)
        self.assertEqual(len(known_ids), 51)

        for memory in listed:
            result = hot_site.retrieve(memory.content, top_k=5)
            self.assertGreaterEqual(
                len(result.matches),
                1,
                f"no retrieval matches for {memory.memory_id}",
            )
            self.assertTrue(
                all(
                    match.memory_id in known_ids
                    for match in result.matches
                ),
                "every retrieved memory must be one of the 51",
            )

    def test_internal_bypass_store_expands_not_evicts(self) -> None:
        """Storing 3x baseline through the backend keeps every item and
        grows current_capacity instead of evicting."""
        hot_site = self.hot_site()
        for index in range(1, 151):
            memory = ValidatedMemory(
                memory_id=f"memory_bypass_{index:03d}",
                content=(
                    f"Bypass capacity fact number {index:03d} "
                    "about the bravo quux."
                ),
                source_candidate_id=(
                    f"candidate_bypass_{index:03d}"
                ),
                created_at="2026-07-01T00:00:00+00:00",
                validated_at="2026-07-01T00:00:00+00:00",
                active=True,
                version=1,
                metadata={"importance": 0.5},
            )
            hot_site.store_validated(
                memory,
                validated_by="human_reviewer",
                validation_reason="Bypass store test.",
            )

        backend = hot_site._backend
        self.assertEqual(len(backend.memory.items), 150)
        self.assertEqual(len(backend.memory.active_items), 150)
        self.assertEqual(len(hot_site.list_memories()), 150)

        status = self.capacity_status()
        self.assertGreaterEqual(status["current_capacity"], 150)
        self.assertEqual(status["active_items"], 150)

    def test_expansion_failure_leaves_candidate_pending(self) -> None:
        """A forced expansion failure keeps the candidate PENDING, appends
        no validated metadata record, and leaves the previous .pt state
        loadable."""
        self.fill(self.gateway, 50)
        lines_before = self.metadata_line_count()

        candidate = self.gateway.propose_memory_candidate(
            content=(
                "Elastic capacity fact number 051 about "
                "the alpha quux."
            ),
            reason="Elastic capacity failure test.",
            source_event_ids=("event_elastic_failure",),
        )

        hot_site = self.hot_site()
        with patch.object(
            hot_site,
            "ensure_capacity_for",
            side_effect=RuntimeError("forced expansion failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.gateway.validate_memory_candidate(
                    candidate.candidate_id,
                    validated_by="human_reviewer",
                    validation_reason="Must not validate.",
                )

        stored = next(
            item
            for item in self.gateway.list_memory_candidates()
            if item.candidate_id == candidate.candidate_id
        )
        self.assertEqual(stored.status, CandidateStatus.PENDING)
        self.assertEqual(
            self.metadata_line_count(),
            lines_before,
            "no validated metadata record may be appended",
        )

        reloaded = self.build_gateway(self.paths)
        self.assertEqual(
            len(
                reloaded._hot_site.list_memories(
                    active_only=True
                )
            ),
            50,
            "previous .pt state must remain loadable",
        )


class ElasticCapacityFormulaTests(ElasticCapacityTestCase):
    def test_compute_expanded_capacity_exact(self) -> None:
        """The pure expansion formula matches the benchmark truth cases."""
        if not _ELASTIC_IMPORTED:
            self.skipTest(
                "memory.hot_site.titan_active_memory."
                "elastic_capacity is not implemented yet."
            )

        self.assertEqual(
            compute_expanded_capacity(
                50,
                active_count=50,
                required_slots=1,
            ),
            63,
            "max(60, ceil(62.5) == 63, 51) == 63",
        )
        self.assertEqual(
            compute_expanded_capacity(
                10,
                active_count=10,
                required_slots=1,
            ),
            20,
            "max(20, ceil(12.5) == 13, 11) == 20",
        )
        self.assertEqual(
            compute_expanded_capacity(
                100,
                active_count=105,
                required_slots=10,
            ),
            125,
            "max(110, 125, 115) == 125",
        )

    def test_elastic_capacity_policy_fields_and_validation(self) -> None:
        """The enforced policy carries the four PRD fields and rejects
        every invalid value."""
        if not _ELASTIC_IMPORTED:
            self.skipTest(
                "memory.hot_site.titan_active_memory."
                "elastic_capacity is not implemented yet."
            )

        policy = ElasticCapacityPolicy()
        self.assertEqual(policy.minimum_growth, 10)
        self.assertEqual(policy.growth_factor, 1.25)
        self.assertEqual(policy.baseline_headroom_ratio, 0.80)
        self.assertEqual(policy.max_automatic_deactivations, 200)
        policy.validate()

        for invalid in (
            dict(minimum_growth=0),
            dict(minimum_growth=-5),
        ):
            with self.assertRaises(ValueError):
                ElasticCapacityPolicy(**invalid).validate()

        for invalid in (
            dict(growth_factor=1.0),
            dict(growth_factor=0.5),
        ):
            with self.assertRaises(ValueError):
                ElasticCapacityPolicy(**invalid).validate()

        for invalid in (
            dict(baseline_headroom_ratio=0.0),
            dict(baseline_headroom_ratio=-0.1),
            dict(baseline_headroom_ratio=1.5),
        ):
            with self.assertRaises(ValueError):
                ElasticCapacityPolicy(**invalid).validate()

        for invalid in (
            dict(max_automatic_deactivations=0),
            dict(max_automatic_deactivations=-1),
        ):
            with self.assertRaises(ValueError):
                ElasticCapacityPolicy(**invalid).validate()

        # Boundary values are valid.
        ElasticCapacityPolicy(
            minimum_growth=1,
            growth_factor=1.01,
            baseline_headroom_ratio=1.0,
            max_automatic_deactivations=1,
        ).validate()

    def test_nightly_capacity_reviewer_constant(self) -> None:
        """The automatic soft-forget reviewer is a fixed constant."""
        if NIGHTLY_CAPACITY_REVIEWER is None:
            self.skipTest(
                "NIGHTLY_CAPACITY_REVIEWER is not implemented yet."
            )
        self.assertEqual(
            NIGHTLY_CAPACITY_REVIEWER,
            "memorix_nightly_capacity",
        )

    def test_should_restore_baseline_headroom_rule(self) -> None:
        """Restoration requires active_count <= floor(baseline * 0.80)."""
        if not _ELASTIC_IMPORTED:
            self.skipTest(
                "memory.hot_site.titan_active_memory."
                "elastic_capacity is not implemented yet."
            )

        # floor(50 * 0.80) == 40
        self.assertTrue(
            should_restore_baseline(
                40,
                baseline_capacity=50,
            ),
            "active 40 <= floor(50 * 0.80) == 40 restores",
        )
        self.assertTrue(
            should_restore_baseline(
                39,
                baseline_capacity=50,
            ),
            "active 39 < floor(50 * 0.80) restores",
        )
        self.assertFalse(
            should_restore_baseline(
                41,
                baseline_capacity=50,
            ),
            "active 41 > floor(50 * 0.80) does not restore",
        )
        self.assertFalse(
            should_restore_baseline(
                50,
                baseline_capacity=50,
            ),
            "active 50 > floor(50 * 0.80) does not restore",
        )

        # A custom headroom ratio is honored: floor(50 * 0.90) == 45.
        self.assertTrue(
            should_restore_baseline(
                45,
                baseline_capacity=50,
                headroom_ratio=0.90,
            )
        )
        self.assertFalse(
            should_restore_baseline(
                46,
                baseline_capacity=50,
                headroom_ratio=0.90,
            )
        )
        self.assertTrue(
            should_restore_baseline(
                50,
                baseline_capacity=50,
                headroom_ratio=1.0,
            )
        )

        for invalid in (
            dict(active_count=-1, baseline_capacity=50),
            dict(active_count=40, baseline_capacity=0),
            dict(
                active_count=40,
                baseline_capacity=50,
                headroom_ratio=0.0,
            ),
            dict(
                active_count=40,
                baseline_capacity=50,
                headroom_ratio=1.5,
            ),
        ):
            with self.assertRaises(ValueError):
                should_restore_baseline(**invalid)


class ElasticCapacityLockTests(ElasticCapacityTestCase):
    def test_lock_contention_raises_and_releases(self) -> None:
        """A held capacity mutation lock rejects a second acquisition;
        after release the expansion API works and the lock file is gone."""
        self.fill(self.gateway, 50)
        self.validate_expansion(self.gateway)
        self.assertEqual(self.capacity_status()["current_capacity"], 63)

        operations = self.gateway._capacity_operations

        with operations.mutation_lock("capacity_expansion"):
            with self.assertRaises(CapacityOperationLockedError):
                with operations.mutation_lock("capacity_expansion"):
                    pass

        self.assertFalse(self.paths.capacity_lock.exists())
        result = self.ensure_capacity()(1)
        self.assertEqual(result, 63)


class ElasticCapacityStatusTests(ElasticCapacityTestCase):
    def test_capacity_status_fields(self) -> None:
        """capacity_status() exposes exactly the enforced 8 fields."""
        self.fill(self.gateway, 5)

        status = self.capacity_status()
        self.assertEqual(
            set(status),
            {
                "baseline_capacity",
                "current_capacity",
                "expansion_active",
                "available_slots",
                "usage_ratio",
                "active_items",
                "inactive_items",
                "total_items",
            },
            "capacity_status must expose exactly the enforced "
            "8 keys and nothing else",
        )

        self.assertEqual(status["baseline_capacity"], 50)
        self.assertEqual(status["current_capacity"], 50)
        self.assertFalse(status["expansion_active"])
        self.assertEqual(status["available_slots"], 45)
        self.assertAlmostEqual(status["usage_ratio"], 0.1)
        self.assertEqual(status["active_items"], 5)
        self.assertEqual(status["inactive_items"], 0)
        self.assertEqual(status["total_items"], 5)


class ElasticCapacityMultiUnitAdmissionTests(ElasticCapacityTestCase):
    """Admission reserves one capacity slot per memory unit before any
    unit is stored; the reserved capacity persists and validation stays
    atomic on an injected storage failure."""

    MULTI_UNIT_CONTENT = " ".join(
        f"Admission unit alpha {index:02d} stays blue."
        for index in range(1, 21)
    )

    def propose_multi_unit_candidate(self) -> str:
        candidate = self.gateway.propose_memory_candidate(
            content=self.MULTI_UNIT_CONTENT,
            reason="Multi-unit admission test.",
            source_event_ids=("event_multi_unit",),
        )
        return candidate.candidate_id

    def read_capacity_events(self) -> list[dict]:
        path = self.paths.capacity_events
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_multi_unit_admission_reserves_all_units_once(self) -> None:
        """Baseline 50 with 49 items and a 20-unit candidate expands once
        to exactly 69 before the first unit is stored."""
        self.fill(self.gateway, 49)
        status = self.capacity_status()
        self.assertEqual(status["current_capacity"], 50)
        self.assertEqual(status["baseline_capacity"], 50)

        units = split_memory_units(self.MULTI_UNIT_CONTENT)
        self.assertEqual(len(units), 20)

        validated = self.gateway.validate_memory_candidate(
            self.propose_multi_unit_candidate(),
            validated_by="human_reviewer",
            validation_reason="Multi-unit admission test.",
        )
        self.assertTrue(validated.memory_id)

        status = self.capacity_status()
        self.assertEqual(
            status["current_capacity"],
            69,
            "max(50 + 10, ceil(50 * 1.25) == 63, 49 + 20) == 69",
        )
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertTrue(status["expansion_active"])
        self.assertEqual(
            len(self.hot_site()._backend.memory.active_items),
            69,
            "all 49 existing plus all 20 units are stored as Titan items",
        )
        self.assertEqual(
            len(self.hot_site().list_memories(active_only=True)),
            50,
            "one metadata record per validated memory: 49 fill + 1 "
            "multi-unit record",
        )

        expansions = [
            event
            for event in self.read_capacity_events()
            if event.get("event_type") == "capacity_expanded"
        ]
        self.assertEqual(
            len(expansions),
            1,
            "capacity must be expanded exactly once, before storage",
        )
        self.assertEqual(expansions[0]["required_slots"], 20)
        self.assertEqual(expansions[0]["capacity_before"], 50)
        self.assertEqual(expansions[0]["capacity_after"], 69)

        backend = self.hot_site()._backend
        record = next(
            record
            for record in backend.list_metadata()
            if record.get("memory_id") == validated.memory_id
        )
        self.assertEqual(len(record.get("titan_item_ids", [])), 20)

    def test_multi_unit_expansion_persists_and_all_units_retrievable(
        self,
    ) -> None:
        """After restart the expansion persists (69/50) and every one of
        the 20 units is retrievable."""
        self.fill(self.gateway, 49)
        candidate_id = self.propose_multi_unit_candidate()
        self.gateway.validate_memory_candidate(
            candidate_id,
            validated_by="human_reviewer",
            validation_reason="Multi-unit admission test.",
        )

        self.gateway = self.build_gateway(self.paths)

        status = self.capacity_status()
        self.assertEqual(status["current_capacity"], 69)
        self.assertEqual(status["baseline_capacity"], 50)
        self.assertTrue(status["expansion_active"])
        self.assertEqual(
            len(self.hot_site()._backend.memory.active_items),
            69,
            "all 20 units survive the restart as Titan items",
        )
        self.assertEqual(
            len(self.hot_site().list_memories(active_only=True)),
            50,
        )

        for unit in split_memory_units(self.MULTI_UNIT_CONTENT):
            result = self.hot_site().retrieve(unit, top_k=5)
            self.assertGreaterEqual(
                len(result.matches),
                1,
                f"no retrieval matches for {unit!r}",
            )

    def test_multi_unit_store_failure_keeps_candidate_pending(self) -> None:
        """An injected save failure after the successful reservation leaves
        the candidate PENDING, appends no validated metadata, and keeps the
        previous valid Titan state recoverable (49 memories, capacity 69)."""
        self.fill(self.gateway, 49)
        lines_before = self.metadata_line_count()
        candidate_id = self.propose_multi_unit_candidate()

        backend = self.hot_site()._backend
        original_save = backend.memory.save
        calls = {"count": 0}

        def flaky_save(path=None):
            calls["count"] += 1
            if calls["count"] >= 2:
                raise RuntimeError("forced storage save failure")
            return original_save(path)

        with patch.object(
            backend.memory,
            "save",
            side_effect=flaky_save,
        ):
            with self.assertRaises(RuntimeError):
                self.gateway.validate_memory_candidate(
                    candidate_id,
                    validated_by="human_reviewer",
                    validation_reason="Must not validate.",
                )

        stored = next(
            item
            for item in self.gateway.list_memory_candidates()
            if item.candidate_id == candidate_id
        )
        self.assertEqual(stored.status, CandidateStatus.PENDING)
        self.assertEqual(
            self.metadata_line_count(),
            lines_before,
            "no validated metadata record may be appended",
        )

        reloaded = self.build_gateway(self.paths)
        self.assertEqual(
            len(
                reloaded._hot_site.list_memories(active_only=True)
            ),
            49,
            "previous .pt state must remain loadable with 49 memories",
        )
        self.assertEqual(
            reloaded._hot_site.capacity_status()["current_capacity"],
            69,
            "the reserved capacity expansion persists durably",
        )


if __name__ == "__main__":
    unittest.main()
