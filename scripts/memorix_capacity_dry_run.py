"""Run isolated dynamic-capacity recommendations.

The script uses simulated block metrics and a temporary recommendation
history. No real memoriX runtime or Titan capacity is modified.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.adaptive import (
    CapacityRecommendationInput,
    CapacityRecommendationStore,
    PressureObservationInput,
    observe_memory_pressure,
    recommend_dynamic_capacity,
)


def recommendation(
    *,
    block_id: str,
    used_items: int,
    usage_samples: tuple[int, ...],
    term_frequencies: dict[str, int],
    surprise_samples: tuple[float, ...],
    previous_pressure_samples: tuple[float, ...],
):
    pressure = observe_memory_pressure(
        PressureObservationInput(
            scope_id=block_id,
            used_items=used_items,
            capacity=100,
            usage_samples=usage_samples,
            term_frequencies=term_frequencies,
            surprise_samples=surprise_samples,
            previous_pressure_samples=(
                previous_pressure_samples
            ),
        )
    )

    return recommend_dynamic_capacity(
        CapacityRecommendationInput(
            block_id=block_id,
            current_capacity=100,
            used_items=used_items,
            pressure=pressure,
        )
    )


def main() -> int:
    stable = recommendation(
        block_id="block_stable",
        used_items=35,
        usage_samples=(25, 30, 35),
        term_frequencies={
            "alpha": 3,
            "beta": 1,
        },
        surprise_samples=(0.2, 0.3),
        previous_pressure_samples=(
            0.2,
            0.3,
            0.4,
        ),
    )

    spike = recommendation(
        block_id="block_spike",
        used_items=95,
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

    persistent = recommendation(
        block_id="block_persistent",
        used_items=92,
        usage_samples=(65, 76, 84, 92),
        term_frequencies={
            "alpha": 3,
            "beta": 3,
            "gamma": 3,
            "delta": 3,
        },
        surprise_samples=(0.7, 0.8, 0.9),
        previous_pressure_samples=(
            0.75,
            0.80,
            0.78,
            0.82,
        ),
    )

    recommendations = (
        stable,
        spike,
        persistent,
    )

    with tempfile.TemporaryDirectory(
        prefix="memorix-capacity-dry-run-"
    ) as root:
        store = CapacityRecommendationStore(
            Path(root)
            / "adaptive"
            / "capacity_recommendations.jsonl"
        )

        for item in recommendations:
            store.append(item)

        result = {
            "mode": "dry_run",
            "runtime": "temporary",
            "capacity_modified": False,
            "recommendations": [
                item.to_dict()
                for item in recommendations
            ],
            "history": store.read_all(),
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

        if any(
            not item.dry_run
            or item.applied
            for item in recommendations
        ):
            return 1

        if stable.recommended_increment != 0:
            return 2

        if spike.recommended_increment != 0:
            return 3

        if persistent.recommended_increment <= 0:
            return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
