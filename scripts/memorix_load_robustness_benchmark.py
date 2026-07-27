from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.load_robustness import run_load_robustness, validate_load_robustness_report


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", required=True)
    run_parser.add_argument("--record-count", type=int, default=5000)
    run_parser.add_argument("--corruption-lines", type=int, default=3)
    run_parser.add_argument("--near-capacity-ratio", type=float, default=0.95)
    run_parser.add_argument("--timeout-seconds", type=float, default=1.0)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--report", required=True)
    args = parser.parse_args()

    if args.command == "run":
        report = run_load_robustness(
            output_root=Path(args.output),
            record_count=args.record_count,
            corruption_lines=args.corruption_lines,
            near_capacity_ratio=args.near_capacity_ratio,
            timeout_seconds=args.timeout_seconds,
        )
        print("MEMORIX_LOAD_ROBUSTNESS_OK")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    report = validate_load_robustness_report(Path(args.report))
    print("MEMORIX_LOAD_ROBUSTNESS_REPORT_VALID")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
