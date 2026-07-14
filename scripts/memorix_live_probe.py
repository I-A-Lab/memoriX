"""Run a read-only diagnostic probe against a memoriX runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.diagnostics import (
    ProbeStatus,
    run_live_probe,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a memoriX runtime without "
            "initializing or modifying it."
        )
    )

    parser.add_argument(
        "runtime_root",
        type=Path,
        help="Path to the memoriX runtime root.",
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON.",
    )

    return parser


def main() -> int:
    arguments = build_parser().parse_args()

    report = run_live_probe(
        arguments.runtime_root
    )

    print(
        json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            indent=(
                None
                if arguments.compact
                else 2
            ),
            sort_keys=True,
        )
    )

    if report.status is ProbeStatus.UNAVAILABLE:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
