#!/usr/bin/env python3
"""Read-only memoriX adaptive-retention ranking CLI."""
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

from memory.adaptive import inspect_runtime_retention_ranking
from memory.data.paths import DEFAULT_RUNTIME_ROOT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rank persisted hot-site memories by adaptive retention score "
            "without mutation or Titan loading."
        )
    )
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--assessment-limit", type=int, default=100)
    parser.add_argument("--simulate-count", type=int)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = inspect_runtime_retention_ranking(
            runtime_root=args.runtime_root,
            assessment_limit=args.assessment_limit,
            simulated_memory_count=args.simulate_count,
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
        return 2

    print(
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=True,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
