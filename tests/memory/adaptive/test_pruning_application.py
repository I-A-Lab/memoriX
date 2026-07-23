from __future__ import annotations

import tempfile
import unittest

import torch

from memory.adaptive import (
    HotMemoryPruningInput,
    PressureObservationInput,
    SoftPruningAction,
    observe_memory_pressure,
    plan_soft_pruning,
)
from memory.data import MemoryStoragePaths, ValidatedMemory
from memory.gateway import apply_soft_pruning_plan
from memory.hot_site.titan_active_memory import HotSiteTitanMemory


class SoftPruningApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.paths = MemoryStoragePaths.from_runtime_root(temporary.name)
        torch.manual_seed(42)
        self.hot_site = HotSiteTitanMemory(
            neural_state_path=self.paths.titan_neural_state,
            metadata_path=self.paths.titan_metadata,
            d_model=32,
            hidden_dim=32,
            max_items=20,
            device="cpu",
            top_k=5,
            min_score=0.0,
        )

    def store(self, memory_id: str, content: str) -> None:
        self.hot_site.store_validated(
            ValidatedMemory(
                memory_id=memory_id,
                content=content,
                source_candidate_id=f"candidate_{memory_id}",
                metadata={"importance": 0.05},
            ),
            validated_by="reviewer",
            validation_reason="Fixture.",
        )

    def make_plan(self):
        pressure = observe_memory_pressure(
            PressureObservationInput(
                scope_id="hot_site",
                used_items=100,
                capacity=100,
                usage_samples=(80, 90, 100),
                term_frequencies={"memory": 1, "pressure": 1},
                surprise_samples=(0.9,),
                previous_pressure_samples=(0.9, 0.95),
                observed_at="2026-07-17T00:00:00+00:00",
            ),
            observation_id="pressure_apply",
        )
        return plan_soft_pruning(
            scope_id="hot_site",
            memories=(
                HotMemoryPruningInput(
                    memory_id="memory_weak",
                    block_id="hot_site",
                    importance=0.0,
                    access_count=0,
                    age_days=365,
                    retrieval_score=0.0,
                ),
                HotMemoryPruningInput(
                    memory_id="memory_pinned",
                    block_id="hot_site",
                    importance=0.0,
                    access_count=0,
                    age_days=365,
                    retrieval_score=0.0,
                    pinned=True,
                ),
            ),
            pressure=pressure,
            plan_id="plan_apply",
            created_at="2026-07-17T00:00:00+00:00",
        )

    def test_dry_run_plan_does_not_mutate_until_applied(self) -> None:
        self.store("memory_weak", "Weak old memory.")
        self.store("memory_pinned", "Pinned memory.")
        plan = self.make_plan()
        self.assertEqual(
            next(r.action for r in plan.recommendations if r.memory_id == "memory_weak"),
            SoftPruningAction.DEACTIVATE,
        )
        self.assertEqual(len(self.hot_site.list_memories(active_only=True)), 2)

        report = apply_soft_pruning_plan(
            plan,
            self.hot_site,
            applied_by="reviewer",
            reason="Controlled capacity recovery.",
        )

        self.assertEqual(report.applied_memory_ids, ("memory_weak",))
        active_ids = {m.memory_id for m in self.hot_site.list_memories(active_only=True)}
        self.assertEqual(active_ids, {"memory_pinned"})
        self.assertFalse(self.paths.cold_archive_events.exists())
        self.assertTrue(report.hot_site_only)
        self.assertTrue(report.cold_site_untouched)
        self.assertFalse(report.physical_deletion)

    def test_application_limit_is_respected(self) -> None:
        self.store("memory_weak", "Weak old memory.")
        plan = self.make_plan()
        report = apply_soft_pruning_plan(
            plan,
            self.hot_site,
            applied_by="reviewer",
            reason="Controlled capacity recovery.",
            max_deactivations=1,
        )
        self.assertEqual(len(report.applied_memory_ids), 1)
