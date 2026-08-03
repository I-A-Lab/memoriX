from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

REPOSITORY_ROOT = find_repository_root(Path(__file__))

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.ablation_benchmark import (
    run_ablation_benchmark,
    validate_ablation_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument(
        "--configurations",
        nargs="*",
    )

    validate_parser = subparsers.add_parser(
        "validate"
    )
    validate_parser.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    if args.command == "run":
        report = run_ablation_benchmark(
            output_root=Path(args.output),
            configurations=args.configurations,
        )
        print("MEMORIX_ABLATION_BENCHMARK_OK")
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = validate_ablation_report(
        Path(args.report)
    )
    print("MEMORIX_ABLATION_REPORT_VALID")
    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
