from __future__ import annotations

import math
import unittest

from memory.adaptive import (
    MemoryPressureInput,
    MemoryPressureWeights,
    PressureLevel,
    assess_memory_pressure,
    normalize_age,
    normalize_low_usage,
    normalize_non_negative,
    normalize_unit,
    observe_hot_site_pressure,
)


class MemoryPressureNormalizationTests(unittest.TestCase):
    def test_unit_normalization_handles_bounds_and_non_finite_values(self) -> None:
        self.assertEqual(normalize_unit(-1), 0.0)
        self.assertEqual(normalize_unit(2), 1.0)
        self.assertEqual(normalize_unit(float("nan")), 0.0)
        self.assertEqual(normalize_unit(float("inf"), default=0.4), 0.4)

    def test_non_negative_normalization(self) -> None:
        self.assertEqual(normalize_non_negative(-2), 0.0)
        self.assertEqual(normalize_non_negative(None), 0.0)

    def test_age_and_usage_are_bounded(self) -> None:
        self.assertEqual(normalize_age(365), 1.0)
        self.assertEqual(normalize_age(-10), 0.0)
        self.assertEqual(normalize_low_usage(0), 1.0)
        self.assertEqual(normalize_low_usage(20), 0.0)
        self.assertEqual(normalize_low_usage(100), 0.0)

    def test_invalid_normalization_horizons_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_age(1, horizon_days=0)
        with self.assertRaises(ValueError):
            normalize_low_usage(1, saturation_count=0)


class IndividualMemoryPressureTests(unittest.TestCase):
    def test_recent_important_used_memory_is_stable(self) -> None:
        result = assess_memory_pressure(
            MemoryPressureInput(
                memory_id="important",
                age_days=1,
                access_count=20,
                importance=1.0,
                momentum=1.0,
                surprise=1.0,
                observed_at="2026-07-17T00:00:00+00:00",
            ),
            assessment_id="assessment_fixed",
        )
        self.assertEqual(result.level, PressureLevel.STABLE)
        self.assertEqual(result.recommended_action, "keep")
        self.assertTrue(result.observation_only)
        self.assertFalse(result.applies_changes)
        self.assertFalse(result.cold_site_accessed)

    def test_old_unused_replaced_memory_is_candidate(self) -> None:
        result = assess_memory_pressure(
            MemoryPressureInput(
                memory_id="obsolete",
                age_days=730,
                access_count=0,
                importance=0.0,
                momentum=0.0,
                surprise=0.0,
                active=False,
                replaced=True,
            )
        )
        self.assertEqual(result.level, PressureLevel.CRITICAL)
        self.assertEqual(result.recommended_action, "deactivate_candidate")
        self.assertGreaterEqual(result.pressure_score, 0.85)

    def test_protected_memory_is_never_deactivation_candidate(self) -> None:
        result = assess_memory_pressure(
            MemoryPressureInput(
                memory_id="protected",
                age_days=1000,
                access_count=0,
                importance=0.0,
                active=False,
                replaced=True,
                protected=True,
            )
        )
        self.assertEqual(result.recommended_action, "keep_protected")

    def test_custom_weights_are_deterministic(self) -> None:
        source = MemoryPressureInput(memory_id="weighted", age_days=365, access_count=20, observed_at="2026-07-17T00:00:00+00:00")
        weights = MemoryPressureWeights(age=1.0, low_usage=0.0, low_importance=0.0, low_momentum=0.0, low_surprise=0.0, inactive=0.0, replaced=0.0)
        first = assess_memory_pressure(source, weights=weights, assessment_id="fixed")
        second = assess_memory_pressure(source, weights=weights, assessment_id="fixed")
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.pressure_score, 1.0)

    def test_invalid_memory_id_and_weights_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assess_memory_pressure(MemoryPressureInput(memory_id=" "))
        with self.assertRaises(ValueError):
            assess_memory_pressure(MemoryPressureInput(memory_id="x"), weights=MemoryPressureWeights(age=-1.0))


class HotSitePressureSnapshotTests(unittest.TestCase):
    def test_empty_snapshot_is_safe(self) -> None:
        snapshot = observe_hot_site_pressure((), observed_at="2026-07-17T00:00:00+00:00", snapshot_id="snapshot")
        self.assertEqual(snapshot.memory_count, 0)
        self.assertEqual(snapshot.mean_pressure, 0.0)
        self.assertEqual(snapshot.maximum_pressure, 0.0)
        self.assertEqual(snapshot.pruning_candidate_count, 0)

    def test_snapshot_is_sorted_and_aggregated(self) -> None:
        memories = (
            MemoryPressureInput(memory_id="z", age_days=730, access_count=0, importance=0.0, active=False, replaced=True),
            MemoryPressureInput(memory_id="a", age_days=0, access_count=20, importance=1.0, momentum=1.0, surprise=1.0, protected=True),
        )
        snapshot = observe_hot_site_pressure(memories, observed_at="2026-07-17T00:00:00+00:00", snapshot_id="snapshot")
        self.assertEqual([item.memory_id for item in snapshot.assessments], ["a", "z"])
        self.assertEqual(snapshot.memory_count, 2)
        self.assertEqual(snapshot.protected_count, 1)
        self.assertEqual(snapshot.inactive_count, 1)
        self.assertEqual(snapshot.replaced_count, 1)
        self.assertEqual(snapshot.pruning_candidate_count, 1)
        self.assertTrue(snapshot.observation_only)
        self.assertFalse(snapshot.applies_changes)
        self.assertFalse(snapshot.cold_site_accessed)


if __name__ == "__main__":
    unittest.main()
