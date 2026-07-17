"""Run the bounded memoriX capacity-saturation benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from memory.benchmark.capacity_saturation import (
    DEFAULT_SCENARIOS,
    run_capacity_saturation_benchmark,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark memoriX saturation calculations without allocating "
            "the simulated memory population."
        )
    )
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--capacity", type=int, default=50_000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--scenarios",
        nargs="+",
        type=int,
        default=list(DEFAULT_SCENARIOS),
    )
    parser.add_argument("--output")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = run_capacity_saturation_benchmark(
            runtime_root=args.runtime_root,
            configured_capacity=args.capacity,
            repetitions=args.repetitions,
            scenarios=args.scenarios,
        )
    except (RuntimeError, ValueError) as error:
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

    payload = report.to_dict()
    indent = 2 if args.pretty else None
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )
    print(encoded)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded + "\n", encoding="utf-8")

    if not report.synthetic_data_only:
        return 3
    if report.runtime_modified:
        return 4
    if report.cold_site_accessed:
        return 5
    if report.actions_applied:
        return 6
    if len(report.results) != len(args.scenarios):
        return 7

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
