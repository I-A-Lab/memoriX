from __future__ import annotations

import unittest

from memory.adaptive import (
    PressureComponents,
    PressureLevel,
    PressureObservationInput,
    PressureThresholds,
    PressureWeights,
    calculate_entropy,
    calculate_memory_pressure,
    calculate_momentum,
    calculate_pressure_persistence,
    calculate_surprise,
    calculate_usage_ratio,
    classify_pressure_level,
    observe_memory_pressure,
)


class UsageRatioTests(unittest.TestCase):
    def test_usage_ratio_is_normalized(self) -> None:
        self.assertEqual(
            calculate_usage_ratio(25, 100),
            0.25,
        )
        self.assertEqual(
            calculate_usage_ratio(150, 100),
            1.0,
        )

    def test_capacity_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            calculate_usage_ratio(0, 0)


class MomentumTests(unittest.TestCase):
    def test_positive_growth_produces_momentum(self) -> None:
        value = calculate_momentum(
            (10, 20, 35),
            100,
        )

        self.assertAlmostEqual(
            value,
            0.125,
        )

    def test_decline_does_not_create_negative_pressure(
        self,
    ) -> None:
        self.assertEqual(
            calculate_momentum(
                (40, 30, 20),
                100,
            ),
            0.0,
        )

    def test_single_sample_has_zero_momentum(self) -> None:
        self.assertEqual(
            calculate_momentum(
                (10,),
                100,
            ),
            0.0,
        )


class EntropyTests(unittest.TestCase):
    def test_uniform_terms_have_maximum_entropy(
        self,
    ) -> None:
        self.assertAlmostEqual(
            calculate_entropy(
                {
                    "alpha": 1,
                    "beta": 1,
                    "gamma": 1,
                }
            ),
            1.0,
        )

    def test_single_term_has_zero_entropy(self) -> None:
        self.assertEqual(
            calculate_entropy(
                {"alpha": 10}
            ),
            0.0,
        )

    def test_empty_terms_have_zero_entropy(self) -> None:
        self.assertEqual(
            calculate_entropy({}),
            0.0,
        )


class SurpriseTests(unittest.TestCase):
    def test_surprise_is_window_mean(self) -> None:
        self.assertAlmostEqual(
            calculate_surprise(
                (0.2, 0.4, 0.6)
            ),
            0.4,
        )

    def test_surprise_rejects_invalid_values(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            calculate_surprise((1.5,))


class PersistenceTests(unittest.TestCase):
    def test_persistence_is_fraction_over_threshold(
        self,
    ) -> None:
        self.assertEqual(
            calculate_pressure_persistence(
                (0.8, 0.75, 0.2, 0.9),
                0.7,
            ),
            0.75,
        )

    def test_empty_history_has_zero_persistence(
        self,
    ) -> None:
        self.assertEqual(
            calculate_pressure_persistence(
                (),
                0.7,
            ),
            0.0,
        )


class CombinedPressureTests(unittest.TestCase):
    def test_weighted_pressure_is_deterministic(
        self,
    ) -> None:
        components = PressureComponents(
            usage_ratio=1.0,
            momentum=0.5,
            entropy=0.5,
            surprise=0.5,
            persistence=0.5,
        )

        value = calculate_memory_pressure(
            components,
            PressureWeights(),
        )

        self.assertAlmostEqual(
            value,
            0.7,
        )

    def test_classification_does_not_recommend_action(
        self,
    ) -> None:
        self.assertEqual(
            classify_pressure_level(0.49),
            PressureLevel.STABLE,
        )
        self.assertEqual(
            classify_pressure_level(0.50),
            PressureLevel.WATCH,
        )
        self.assertEqual(
            classify_pressure_level(0.70),
            PressureLevel.HIGH,
        )
        self.assertEqual(
            classify_pressure_level(0.85),
            PressureLevel.CRITICAL,
        )


class ObservationTests(unittest.TestCase):
    def test_observation_contains_all_components(
        self,
    ) -> None:
        observation = observe_memory_pressure(
            PressureObservationInput(
                scope_id="hot_site",
                used_items=80,
                capacity=100,
                usage_samples=(
                    40,
                    55,
                    70,
                    80,
                ),
                term_frequencies={
                    "memory": 4,
                    "agent": 3,
                    "titan": 2,
                },
                surprise_samples=(
                    0.3,
                    0.6,
                    0.9,
                ),
                previous_pressure_samples=(
                    0.72,
                    0.74,
                    0.2,
                ),
                observed_at=(
                    "2026-07-14T10:00:00+00:00"
                ),
            ),
            observation_id=(
                "pressure_test"
            ),
        )

        self.assertEqual(
            observation.observation_id,
            "pressure_test",
        )
        self.assertEqual(
            observation.scope_id,
            "hot_site",
        )
        self.assertTrue(
            observation.observation_only
        )
        self.assertGreaterEqual(
            observation.memory_pressure,
            0.0,
        )
        self.assertLessEqual(
            observation.memory_pressure,
            1.0,
        )
        self.assertEqual(
            observation.used_items,
            80,
        )
        self.assertEqual(
            observation.capacity,
            100,
        )
        self.assertIn(
            "usage_ratio",
            observation.components.as_dict(),
        )
        self.assertTrue(
            any(
                "No expansion" in line
                for line in observation.explanation
            )
        )

    def test_observation_validates_input(self) -> None:
        with self.assertRaises(ValueError):
            observe_memory_pressure(
                PressureObservationInput(
                    scope_id="",
                    used_items=0,
                    capacity=100,
                )
            )

    def test_custom_thresholds_are_supported(
        self,
    ) -> None:
        observation = observe_memory_pressure(
            PressureObservationInput(
                scope_id="block_test",
                used_items=50,
                capacity=100,
            ),
            thresholds=PressureThresholds(
                watch=0.1,
                high=0.19,
                critical=0.3,
                persistence=0.7,
            ),
        )

        self.assertIn(
            observation.level,
            {
                PressureLevel.HIGH,
                PressureLevel.CRITICAL,
            },
        )


if __name__ == "__main__":
    unittest.main()
