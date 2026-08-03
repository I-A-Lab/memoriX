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

from memory.benchmark.reference_campaign import (
    CampaignRequest,
    run_reference_campaign,
    validate_reference_campaign,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run = commands.add_parser("run")
    run.add_argument("--output", required=True)
    run.add_argument("--archive")
    run.add_argument(
        "--size",
        choices=("small", "medium"),
        default="small",
    )
    run.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=[101, 202, 303],
    )
    run.add_argument(
        "--profile-count",
        type=int,
        default=12,
    )
    run.add_argument(
        "--project-count",
        type=int,
        default=12,
    )
    run.add_argument(
        "--top-k",
        type=int,
        default=5,
    )
    run.add_argument(
        "--configs-dir",
        default=str(
            REPOSITORY_ROOT
            / "benchmarks"
            / "memorix_vs_no_memory"
            / "configs"
        ),
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
        request = CampaignRequest(
            size=args.size,
            seeds=tuple(args.seeds),
            profile_count=args.profile_count,
            project_count=args.project_count,
            top_k=args.top_k,
        )
        report = run_reference_campaign(
            output_root=Path(args.output),
            configs_dir=Path(
                args.configs_dir
            ),
            request=request,
            archive_path=(
                None
                if args.archive is None
                else Path(args.archive)
            ),
        )
        print(
            "MEMORIX_REFERENCE_CAMPAIGN_OK"
        )
        print(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = validate_reference_campaign(
        Path(args.report)
    )
    print(
        "MEMORIX_REFERENCE_CAMPAIGN_VALID"
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
