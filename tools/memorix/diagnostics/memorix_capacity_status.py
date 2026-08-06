#!/usr/bin/env python3
"""Read-only memoriX runtime capacity diagnostic and simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.adaptive.runtime_capacity import inspect_runtime_capacity
from memory.data.paths import DEFAULT_RUNTIME_ROOT
from memory.hot_site.titan_active_memory.config import (
    load_titan_memory_config,
)

EXIT_VALIDATION = 2


def build_parser() -> argparse.ArgumentParser:
    config = load_titan_memory_config()
    parser = argparse.ArgumentParser(
        description=(
            "Inspect memoriX hot-site capacity without loading Titan "
            "or modifying runtime data."
        )
    )
    parser.add_argument(
        "--runtime-root",
        default=str(DEFAULT_RUNTIME_ROOT),
    )
    parser.add_argument(
        "--capacity",
        type=int,
        default=config.max_items,
    )
    parser.add_argument(
        "--simulate-active-items",
        type=int,
    )
    parser.add_argument(
        "--simulate-inactive-items",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--simulate-pending-candidates",
        type=int,
        default=0,
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--pretty", action="store_true")
    output.add_argument("--compact", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        snapshot = inspect_runtime_capacity(
            runtime_root=args.runtime_root,
            configured_capacity=args.capacity,
            simulated_active_items=(
                args.simulate_active_items
            ),
            simulated_inactive_items=(
                args.simulate_inactive_items
            ),
            simulated_pending_candidates=(
                args.simulate_pending_candidates
            ),
        )
    except (TypeError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "validation_failed",
                    "message": str(error),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return EXIT_VALIDATION

    print(
        json.dumps(
            snapshot.to_dict(),
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=True,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
