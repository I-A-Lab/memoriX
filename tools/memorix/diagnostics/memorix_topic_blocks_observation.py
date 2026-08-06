"""Observe dynamic topic blocks in an isolated temporary registry.

No real memoriX runtime is read or modified.
"""

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
    TopicBlockInput,
    TopicBlockRegistry,
    observe_topic_block,
)


def main() -> int:
    simulated_items = (
        TopicBlockInput(
            content=(
                "Astronomy telescope stars and "
                "astronomy observations."
            ),
            item_id="simulated_astronomy_one",
            metadata_terms=(
                "space",
                "astronomy",
            ),
            importance=0.8,
            capacity=10,
            used_items=1,
            observed_at=(
                "2026-07-14T10:00:00+00:00"
            ),
        ),
        TopicBlockInput(
            content=(
                "Astronomy planets stars and "
                "astronomy research."
            ),
            item_id="simulated_astronomy_two",
            metadata_terms=(
                "astronomy",
            ),
            importance=0.7,
            capacity=10,
            used_items=1,
            observed_at=(
                "2026-07-14T11:00:00+00:00"
            ),
        ),
        TopicBlockInput(
            content=(
                "Guitar melody concert and "
                "guitar performance."
            ),
            item_id="simulated_music_one",
            metadata_terms=(
                "music",
            ),
            importance=0.6,
            capacity=10,
            used_items=1,
            observed_at=(
                "2026-07-14T12:00:00+00:00"
            ),
        ),
    )

    with tempfile.TemporaryDirectory(
        prefix="memorix-topic-blocks-"
    ) as temporary_root:
        registry = TopicBlockRegistry(
            Path(temporary_root)
            / "adaptive"
            / "topic_blocks.json"
        )

        observations = []

        for source in simulated_items:
            observation = observe_topic_block(
                source
            )

            observations.append(
                observation.to_dict()
            )

            registry.upsert_observation(
                observation
            )

        result = {
            "mode": "observation_only",
            "runtime": "temporary",
            "observations": observations,
            "registry": registry.read(),
        }

        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
