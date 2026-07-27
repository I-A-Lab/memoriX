from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPOSITORY_ROOT),
    )

from memory.benchmark.final_report import (
    generate_final_report,
    validate_final_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    generate_parser = subparsers.add_parser(
        "generate"
    )
    generate_parser.add_argument(
        "--multiseed-report",
        required=True,
    )
    generate_parser.add_argument(
        "--output",
        required=True,
    )

    validate_parser = subparsers.add_parser(
        "validate"
    )
    validate_parser.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    if args.command == "generate":
        report = generate_final_report(
            multiseed_report_path=Path(
                args.multiseed_report
            ),
            output_root=Path(
                args.output
            ),
        )
        print(
            "MEMORIX_FINAL_REPORT_GENERATED"
        )
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = validate_final_report(
        Path(args.report)
    )

    print(
        "MEMORIX_FINAL_REPORT_VALID"
    )
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
