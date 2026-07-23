from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.benchmark.capacity_saturation import (
    DEFAULT_SCENARIOS,
    PLAN_SAMPLE_LIMIT,
    run_capacity_saturation_benchmark,
)


class CapacitySaturationBenchmarkTests(unittest.TestCase):
    def test_default_scenarios_are_bounded_and_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_root = Path(temp) / "missing-runtime"
            report = run_capacity_saturation_benchmark(
                runtime_root=runtime_root,
                configured_capacity=50_000,
                repetitions=1,
            )

            self.assertEqual(
                tuple(item.active_items for item in report.results),
                DEFAULT_SCENARIOS,
            )
            self.assertFalse(runtime_root.exists())
            self.assertTrue(report.synthetic_data_only)
            self.assertFalse(report.runtime_modified)
            self.assertFalse(report.cold_site_accessed)
            self.assertFalse(report.actions_applied)
            self.assertTrue(
                all(
                    item.bounded_plan_sample_size <= PLAN_SAMPLE_LIMIT
                    for item in report.results
                )
            )

    def test_six_million_scenario_is_critical_without_admission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = run_capacity_saturation_benchmark(
                runtime_root=Path(temp) / "runtime",
                configured_capacity=50_000,
                repetitions=1,
                scenarios=(6_000_000,),
            )

            result = report.results[0]
            self.assertEqual(result.usage_ratio, 120.0)
            self.assertEqual(result.pressure_level, "critical")
            self.assertFalse(result.admission_allowed)
            self.assertEqual(result.available_slots, 0)
            self.assertEqual(result.required_free_slots, 5_950_001)
            self.assertEqual(
                result.bounded_plan_sample_size,
                PLAN_SAMPLE_LIMIT,
            )

    def test_invalid_inputs_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runtime"

            with self.assertRaises(ValueError):
                run_capacity_saturation_benchmark(
                    runtime_root=root,
                    configured_capacity=0,
                )

            with self.assertRaises(ValueError):
                run_capacity_saturation_benchmark(
                    runtime_root=root,
                    repetitions=0,
                )

            with self.assertRaises(ValueError):
                run_capacity_saturation_benchmark(
                    runtime_root=root,
                    scenarios=(-1,),
                )


if __name__ == "__main__":
    unittest.main()
