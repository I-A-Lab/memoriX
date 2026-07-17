#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.benchmark import run_retention_ranking_benchmark
from memory.data.paths import DEFAULT_RUNTIME_ROOT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run bounded synthetic adaptive-retention benchmarks."
    )
    parser.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--assessment-limit", type=int, default=1)
    parser.add_argument("--output")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = run_retention_ranking_benchmark(
            runtime_root=args.runtime_root,
            repetitions=args.repetitions,
            assessment_limit=args.assessment_limit,
        )
    except (TypeError, ValueError) as error:
        print(
            json.dumps(
                {"status": "validation_failed", "message": str(error)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    text = json.dumps(
        report,
        indent=2 if args.pretty else None,
        sort_keys=True,
        separators=None if args.pretty else (",", ":"),
    )
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
