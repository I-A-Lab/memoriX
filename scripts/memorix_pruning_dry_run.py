"""Run an isolated hot-site-only soft-pruning simulation."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.adaptive import (
    HotMemoryPruningInput,
    PressureObservationInput,
    SoftPruningAction,
    SoftPruningPlanStore,
    observe_memory_pressure,
    plan_soft_pruning,
)


def main() -> int:
    block_id = "block_pruning_simulation"

    pressure = observe_memory_pressure(
        PressureObservationInput(
            scope_id=block_id,
            used_items=96,
            capacity=100,
            usage_samples=(65, 78, 88, 96),
            term_frequencies={
                "alpha": 1,
                "beta": 1,
                "gamma": 1,
                "delta": 1,
            },
            surprise_samples=(0.8, 0.9),
            previous_pressure_samples=(
                0.8,
                0.82,
                0.85,
            ),
        ),
        observation_id="pressure_pruning_simulation",
    )

    memories = (
        HotMemoryPruningInput(
            memory_id="memory_pinned",
            block_id=block_id,
            importance=0.05,
            access_count=0,
            age_days=365,
            retrieval_score=0.05,
            pinned=True,
        ),
        HotMemoryPruningInput(
            memory_id="memory_recent",
            block_id=block_id,
            importance=0.10,
            access_count=0,
            age_days=2,
            retrieval_score=0.05,
        ),
        HotMemoryPruningInput(
            memory_id="memory_weaken",
            block_id=block_id,
            importance=0.30,
            access_count=1,
            age_days=280,
            retrieval_score=0.25,
        ),
        HotMemoryPruningInput(
            memory_id="memory_deactivate",
            block_id=block_id,
            importance=0.02,
            access_count=0,
            age_days=365,
            retrieval_score=0.01,
        ),
    )

    plan = plan_soft_pruning(
        scope_id=block_id,
        memories=memories,
        pressure=pressure,
        plan_id="pruning_simulation",
    )

    with tempfile.TemporaryDirectory(
        prefix="memorix-pruning-dry-run-"
    ) as root:
        store = SoftPruningPlanStore(
            Path(root)
            / "adaptive"
            / "pruning_plans.jsonl"
        )

        store.append(plan)

        result = {
            "mode": "dry_run",
            "runtime": "temporary",
            "hot_site_only": plan.hot_site_only,
            "cold_site_untouched": plan.cold_site_untouched,
            "physical_deletion": plan.physical_deletion,
            "applied": plan.applied,
            "plan": plan.to_dict(),
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

        actions = {
            recommendation.memory_id:
                recommendation.action
            for recommendation
            in plan.recommendations
        }

        if not plan.hot_site_only:
            return 1

        if not plan.cold_site_untouched:
            return 2

        if plan.physical_deletion:
            return 3

        if not plan.dry_run or plan.applied:
            return 4

        if (
            actions["memory_pinned"]
            is not SoftPruningAction.KEEP
        ):
            return 5

        if (
            actions["memory_recent"]
            is not SoftPruningAction.KEEP
        ):
            return 6

        if (
            actions["memory_weaken"]
            is not SoftPruningAction.WEAKEN
        ):
            return 7

        if (
            actions["memory_deactivate"]
            is not SoftPruningAction.DEACTIVATE
        ):
            return 8

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
