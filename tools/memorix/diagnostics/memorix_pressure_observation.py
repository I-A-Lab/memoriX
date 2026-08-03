"""Run one isolated adaptive pressure observation.

This script uses explicit simulated measurements. It does not read or mutate
the real short-term, cold, candidate, or Titan stores.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.adaptive import (
    PressureObservationInput,
    observe_memory_pressure,
)


def main() -> int:
    observation = observe_memory_pressure(
        PressureObservationInput(
            scope_id="simulated_hot_site",
            used_items=82,
            capacity=100,
            usage_samples=(
                50,
                61,
                72,
                82,
            ),
            term_frequencies={
                "memory": 7,
                "agent": 5,
                "titan": 4,
                "retrieval": 3,
            },
            surprise_samples=(
                0.3,
                0.5,
                0.8,
            ),
            previous_pressure_samples=(
                0.72,
                0.75,
                0.20,
            ),
        )
    )

    print(
        json.dumps(
            observation.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
