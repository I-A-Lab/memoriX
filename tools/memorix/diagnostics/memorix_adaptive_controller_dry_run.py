"""Run isolated adaptive-controller dry-run scenarios."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.adaptive import (
    AdaptiveControllerInput,
    AdaptiveDecisionStore,
    HotMemoryPruningInput,
    evaluate_adaptive_controller,
)


def stable_decision():
    block_id = "block_controller_stable"

    return evaluate_adaptive_controller(
        AdaptiveControllerInput(
            scope_id=block_id,
            current_capacity=100,
            used_items=30,
            usage_samples=(20, 25, 30),
            term_frequencies={
                "stable": 5,
            },
            surprise_samples=(0.1, 0.2),
            previous_pressure_samples=(
                0.2,
                0.3,
                0.25,
            ),
            memories=(
                HotMemoryPruningInput(
                    memory_id="memory_stable",
                    block_id=block_id,
                    importance=0.6,
                    access_count=5,
                    age_days=30,
                    retrieval_score=0.6,
                ),
            ),
        ),
        decision_id="adaptive_stable",
    )


def pressured_decision():
    block_id = "block_controller_pressured"

    return evaluate_adaptive_controller(
        AdaptiveControllerInput(
            scope_id=block_id,
            current_capacity=100,
            used_items=95,
            usage_samples=(60, 75, 85, 95),
            term_frequencies={
                "alpha": 1,
                "beta": 1,
                "gamma": 1,
                "delta": 1,
            },
            surprise_samples=(0.8, 0.9),
            previous_pressure_samples=(
                0.80,
                0.82,
                0.85,
            ),
            memories=(
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
            ),
        ),
        decision_id="adaptive_pressured",
    )


def main() -> int:
    stable = stable_decision()
    pressured = pressured_decision()

    with tempfile.TemporaryDirectory(
        prefix="memorix-controller-dry-run-"
    ) as root:
        store = AdaptiveDecisionStore(
            Path(root)
            / "adaptive"
            / "controller_decisions.jsonl"
        )

        store.append(stable)
        store.append(pressured)

        result = {
            "mode": "dry_run",
            "runtime": "temporary",
            "actions_applied": False,
            "hot_site_only": True,
            "cold_site_untouched": True,
            "retrieval_behavior_changed": False,
            "decisions": [
                stable.to_dict(),
                pressured.to_dict(),
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

        if stable.recommended_actions:
            return 1

        if not pressured.recommended_actions:
            return 2

        if pressured.applied:
            return 3

        if not pressured.cold_site_untouched:
            return 4

        if pressured.retrieval_behavior_changed:
            return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
