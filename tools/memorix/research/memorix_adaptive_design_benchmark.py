"""Run the isolated memoriX adaptive-design benchmark."""

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


from memory.benchmark import (
    build_benchmark_scenarios,
    run_adaptive_design_benchmark,
)


def main() -> int:
    summary = run_adaptive_design_benchmark(
        build_benchmark_scenarios(),
        seed=42,
        benchmark_id="memorix_adaptive_designs",
    )

    payload = summary.to_dict()

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )

    if not summary.synthetic_data_only:
        return 1

    if summary.runtime_modified:
        return 2

    if summary.cold_site_accessed:
        return 3

    if summary.actions_applied:
        return 4

    if len(summary.results) != 15:
        return 5

    if len(summary.ranking) != 5:
        return 6

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
