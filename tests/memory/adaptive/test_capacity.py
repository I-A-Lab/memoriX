from __future__ import annotations

import unittest

from memory.adaptive import (
    CapacityPolicy,
    CapacityRecommendationInput,
    CapacityRecommendationLevel,
    PressureObservationInput,
    observe_memory_pressure,
    recommend_dynamic_capacity,
)


def pressure_for(
    *,
    block_id: str,
    used_items: int,
    capacity: int,
    usage_samples: tuple[int, ...],
    term_frequencies: dict[str, int],
    surprise_samples: tuple[float, ...],
    previous_pressure_samples: tuple[float, ...],
):
    return observe_memory_pressure(
        PressureObservationInput(
            scope_id=block_id,
            used_items=used_items,
            capacity=capacity,
            usage_samples=usage_samples,
            term_frequencies=term_frequencies,
            surprise_samples=surprise_samples,
            previous_pressure_samples=(
                previous_pressure_samples
            ),
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        observation_id=(
            f"pressure_{block_id}"
        ),
    )


class DynamicCapacityTests(unittest.TestCase):
    def test_low_usage_keeps_capacity(self) -> None:
        pressure = pressure_for(
            block_id="block_low",
            used_items=30,
            capacity=100,
            usage_samples=(20, 25, 30),
            term_frequencies={
                "alpha": 1,
                "beta": 1,
            },
            surprise_samples=(0.2, 0.3),
            previous_pressure_samples=(
                0.2,
                0.3,
                0.4,
            ),
        )

        recommendation = (
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_low",
                    current_capacity=100,
                    used_items=30,
                    pressure=pressure,
                    evaluated_at=(
                        "2026-07-14T11:00:00+00:00"
                    ),
                ),
                recommendation_id=(
                    "capacity_low"
                ),
            )
        )

        self.assertEqual(
            recommendation.level,
            CapacityRecommendationLevel.KEEP,
        )
        self.assertEqual(
            recommendation.recommended_capacity,
            100,
        )
        self.assertEqual(
            recommendation.recommended_increment,
            0,
        )
        self.assertTrue(recommendation.dry_run)
        self.assertFalse(recommendation.applied)

    def test_single_usage_spike_does_not_expand(
        self,
    ) -> None:
        pressure = pressure_for(
            block_id="block_spike",
            used_items=95,
            capacity=100,
            usage_samples=(20, 20, 95),
            term_frequencies={
                "single": 10,
            },
            surprise_samples=(0.2,),
            previous_pressure_samples=(
                0.2,
                0.3,
                0.25,
            ),
        )

        recommendation = (
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_spike",
                    current_capacity=100,
                    used_items=95,
                    pressure=pressure,
                )
            )
        )

        self.assertNotEqual(
            recommendation.level,
            CapacityRecommendationLevel.EXPAND,
        )
        self.assertIn(
            "pressure_not_persistent",
            recommendation.blocking_reasons,
        )

    def test_persistent_pressure_recommends_expansion(
        self,
    ) -> None:
        pressure = pressure_for(
            block_id="block_expand",
            used_items=92,
            capacity=100,
            usage_samples=(
                65,
                76,
                84,
                92,
            ),
            term_frequencies={
                "alpha": 3,
                "beta": 3,
                "gamma": 3,
                "delta": 3,
            },
            surprise_samples=(
                0.7,
                0.8,
                0.9,
            ),
            previous_pressure_samples=(
                0.75,
                0.80,
                0.78,
                0.82,
            ),
        )

        recommendation = (
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_expand",
                    current_capacity=100,
                    used_items=92,
                    pressure=pressure,
                    evaluated_at=(
                        "2026-07-14T11:00:00+00:00"
                    ),
                ),
                recommendation_id=(
                    "capacity_expand"
                ),
            )
        )

        self.assertEqual(
            recommendation.level,
            CapacityRecommendationLevel.EXPAND,
        )
        self.assertGreater(
            recommendation.recommended_capacity,
            100,
        )
        self.assertGreater(
            recommendation.recommended_increment,
            0,
        )
        self.assertGreaterEqual(
            len(
                recommendation.supporting_signals
            ),
            2,
        )
        self.assertEqual(
            recommendation.blocking_reasons,
            (),
        )

    def test_high_usage_without_enough_signals_watches(
        self,
    ) -> None:
        pressure = pressure_for(
            block_id="block_watch",
            used_items=90,
            capacity=100,
            usage_samples=(89, 90),
            term_frequencies={
                "single": 10,
            },
            surprise_samples=(0.1,),
            previous_pressure_samples=(
                0.8,
                0.8,
                0.8,
            ),
        )

        recommendation = (
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_watch",
                    current_capacity=100,
                    used_items=90,
                    pressure=pressure,
                )
            )
        )

        self.assertEqual(
            recommendation.level,
            CapacityRecommendationLevel.WATCH,
        )
        self.assertEqual(
            recommendation.recommended_capacity,
            100,
        )
        self.assertIn(
            "insufficient_supporting_signals",
            recommendation.blocking_reasons,
        )

    def test_scope_must_match_block(self) -> None:
        pressure = pressure_for(
            block_id="block_one",
            used_items=10,
            capacity=100,
            usage_samples=(10,),
            term_frequencies={},
            surprise_samples=(),
            previous_pressure_samples=(),
        )

        with self.assertRaises(ValueError):
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_two",
                    current_capacity=100,
                    used_items=10,
                    pressure=pressure,
                )
            )

    def test_custom_policy_is_supported(self) -> None:
        pressure = pressure_for(
            block_id="block_custom",
            used_items=60,
            capacity=100,
            usage_samples=(20, 40, 60),
            term_frequencies={
                "a": 1,
                "b": 1,
                "c": 1,
            },
            surprise_samples=(0.6, 0.7),
            previous_pressure_samples=(
                0.6,
                0.7,
                0.8,
            ),
        )

        recommendation = (
            recommend_dynamic_capacity(
                CapacityRecommendationInput(
                    block_id="block_custom",
                    current_capacity=100,
                    used_items=60,
                    pressure=pressure,
                ),
                policy=CapacityPolicy(
                    minimum_usage_ratio=0.50,
                    minimum_memory_pressure=0.40,
                    minimum_persistence=0.50,
                    minimum_momentum=0.05,
                    minimum_entropy=0.50,
                    minimum_surprise=0.50,
                    minimum_supporting_signals=2,
                    minimum_increment=20,
                    normal_growth_factor=1.20,
                    strong_growth_factor=1.40,
                    maximum_growth_factor=1.50,
                ),
            )
        )

        self.assertEqual(
            recommendation.level,
            CapacityRecommendationLevel.EXPAND,
        )
        self.assertGreaterEqual(
            recommendation.recommended_increment,
            20,
        )


if __name__ == "__main__":
    unittest.main()
