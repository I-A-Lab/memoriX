from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[1]
)
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPOSITORY_ROOT),
    )

from memory.benchmark.opencode_resilient_campaign import (
    PROFILE_SPECS,
    ResilientCampaignRequest,
    run_resilient_campaign,
    validate_resilient_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run = commands.add_parser("run")
    run.add_argument("--output", required=True)
    run.add_argument("--archive", required=True)
    run.add_argument(
        "--profile",
        choices=tuple(PROFILE_SPECS),
        default="large",
    )
    run.add_argument("--model")
    run.add_argument(
        "--seeds",
        nargs="+",
        type=int,
    )
    run.add_argument(
        "--task-count",
        type=int,
    )
    run.add_argument(
        "--distractor-count",
        type=int,
    )
    run.add_argument(
        "--timeout-seconds",
        type=int,
    )
    run.add_argument(
        "--top-k",
        type=int,
        default=10,
    )
    run.add_argument(
        "--max-attempts",
        type=int,
        default=3,
    )
    run.add_argument(
        "--retry-wait-seconds",
        type=int,
        default=20,
    )
    run.add_argument(
        "--resume",
        action="store_true",
    )

    validate = commands.add_parser(
        "validate"
    )
    validate.add_argument(
        "--report",
        required=True,
    )

    args = parser.parse_args()

    if args.command == "run":
        report = run_resilient_campaign(
            repository_root=REPOSITORY_ROOT,
            output_root=Path(args.output),
            archive_path=Path(args.archive),
            request=ResilientCampaignRequest(
                profile=args.profile,
                model=args.model,
                seeds=(
                    None
                    if args.seeds is None
                    else tuple(args.seeds)
                ),
                task_count=args.task_count,
                distractor_count=(
                    args.distractor_count
                ),
                timeout_seconds=(
                    args.timeout_seconds
                ),
                top_k=args.top_k,
                max_attempts=(
                    args.max_attempts
                ),
                retry_wait_seconds=(
                    args.retry_wait_seconds
                ),
            ),
            resume=args.resume,
        )
        print(
            "MEMORIX_RESILIENT_OPENCODE_CAMPAIGN_OK"
        )
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = validate_resilient_report(
        Path(args.report)
    )
    print(
        "MEMORIX_RESILIENT_OPENCODE_CAMPAIGN_VALID"
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
