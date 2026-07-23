from __future__ import annotations

import unittest

from memory.benchmark import (
    BenchmarkDesign,
    build_benchmark_scenarios,
    run_adaptive_design_benchmark,
    run_design,
)


class BenchmarkScenarioTests(unittest.TestCase):
    def test_scenarios_cover_three_pressure_modes(
        self,
    ) -> None:
        scenarios = build_benchmark_scenarios()

        self.assertEqual(len(scenarios), 3)

        identifiers = {
            scenario.scenario_id
            for scenario in scenarios
        }

        self.assertEqual(
            identifiers,
            {
                "stable",
                "single_spike",
                "persistent_pressure",
            },
        )


class IndividualDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scenarios = {
            scenario.scenario_id: scenario
            for scenario in (
                build_benchmark_scenarios()
            )
        }

    def test_baseline_has_no_adaptive_actions(
        self,
    ) -> None:
        result = run_design(
            BenchmarkDesign.BASELINE,
            self.scenarios["persistent_pressure"],
        )

        self.assertIsNone(
            result.metrics.pressure_score
        )
        self.assertFalse(
            result.metrics.expansion_recommended
        )
        self.assertEqual(
            result.metrics.pruning_recommendation_count,
            0,
        )

    def test_single_spike_does_not_expand(
        self,
    ) -> None:
        result = run_design(
            BenchmarkDesign.DYNAMIC_CAPACITY,
            self.scenarios["single_spike"],
        )

        self.assertFalse(
            result.metrics.expansion_recommended
        )
        self.assertTrue(
            result.metrics.expected_behavior_matched
        )

    def test_persistent_pressure_expands(
        self,
    ) -> None:
        result = run_design(
            BenchmarkDesign.DYNAMIC_CAPACITY,
            self.scenarios["persistent_pressure"],
        )

        self.assertTrue(
            result.metrics.expansion_recommended
        )
        self.assertTrue(
            result.metrics.expected_behavior_matched
        )

    def test_adaptive_design_preserves_safety(
        self,
    ) -> None:
        result = run_design(
            BenchmarkDesign.ADAPTIVE_CONTROLLER,
            self.scenarios["persistent_pressure"],
        )

        self.assertTrue(
            result.metrics.safety_contracts_preserved
        )
        self.assertTrue(
            result.metrics.expansion_recommended
        )
        self.assertGreater(
            result.metrics.pruning_recommendation_count,
            0,
        )


class FullBenchmarkTests(unittest.TestCase):
    def test_all_designs_and_scenarios_run(
        self,
    ) -> None:
        summary = (
            run_adaptive_design_benchmark(
                build_benchmark_scenarios(),
                seed=42,
                benchmark_id="benchmark_test",
            )
        )

        self.assertEqual(
            summary.benchmark_id,
            "benchmark_test",
        )
        self.assertEqual(
            len(summary.results),
            15,
        )
        self.assertEqual(
            len(summary.ranking),
            5,
        )
        self.assertTrue(
            summary.synthetic_data_only
        )
        self.assertFalse(
            summary.runtime_modified
        )
        self.assertFalse(
            summary.cold_site_accessed
        )
        self.assertFalse(
            summary.actions_applied
        )

    def test_benchmark_is_structurally_reproducible(
        self,
    ) -> None:
        first = run_adaptive_design_benchmark(
            build_benchmark_scenarios(),
            seed=42,
            benchmark_id="benchmark_fixed",
        )

        second = run_adaptive_design_benchmark(
            build_benchmark_scenarios(),
            seed=42,
            benchmark_id="benchmark_fixed",
        )

        first_payload = first.to_dict()
        second_payload = second.to_dict()

        first_payload.pop("created_at")
        second_payload.pop("created_at")

        for payload in (
            first_payload,
            second_payload,
        ):
            for result in payload["results"]:
                result["metrics"].pop(
                    "latency_ms"
                )

        self.assertEqual(
            first_payload,
            second_payload,
        )


if __name__ == "__main__":
    unittest.main()
