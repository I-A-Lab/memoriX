"""Validate and display the Part 29 global benchmark contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.benchmark.global_contracts import load_benchmark_contracts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate memoriX versus no-memory benchmark contracts."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root. Defaults to the automatically detected repository.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = args.project_root.resolve()
    config_root = (
        project_root
        / "benchmarks"
        / "memorix_vs_no_memory"
        / "configs"
    )
    contracts = load_benchmark_contracts(config_root)
    output = contracts.to_dict()
    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
