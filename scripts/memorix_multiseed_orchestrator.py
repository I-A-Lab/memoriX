from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.multiseed_orchestrator import (
    run_multiseed_orchestrator,
    validate_multiseed_report,
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
        "--seeds",
        nargs="+",
        type=int,
        required=True,
    )
    run_parser.add_argument(
        "--modes",
        nargs="+",
        default=["no_memory", "memorix_core"],
    )
    run_parser.add_argument(
        "--suite",
        default="sdlc",
    )
    run_parser.add_argument(
        "--resume",
        action="store_true",
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
        report = run_multiseed_orchestrator(
            output_root=Path(args.output),
            seeds=args.seeds,
            modes=args.modes,
            suite=args.suite,
            resume=args.resume,
        )
        print("MEMORIX_MULTISEED_ORCHESTRATOR_OK")
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = validate_multiseed_report(
        Path(args.report)
    )
    print("MEMORIX_MULTISEED_REPORT_VALID")
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
