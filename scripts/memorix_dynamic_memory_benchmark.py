from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from memory.benchmark.dynamic_memory_lifecycle import (
    PROFILE_SPECS,
    DynamicCampaignRequest,
    run_dynamic_campaign,
    validate_dynamic_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--output", required=True)
    run.add_argument("--archive", required=True)
    run.add_argument(
        "--profile", choices=tuple(PROFILE_SPECS), default="quick"
    )
    run.add_argument("--seeds", nargs="+", type=int)
    run.add_argument("--distractor-count", type=int)
    run.add_argument("--update-count", type=int)
    run.add_argument("--titan-dim", type=int)
    run.add_argument("--top-k", type=int)

    validate = commands.add_parser("validate")
    validate.add_argument("--report", required=True)

    args = parser.parse_args()
    if args.command == "run":
        report = run_dynamic_campaign(
            repository_root=REPOSITORY_ROOT,
            output_root=Path(args.output),
            archive_path=Path(args.archive),
            request=DynamicCampaignRequest(
                profile=args.profile,
                seeds=None if args.seeds is None else tuple(args.seeds),
                distractor_count=args.distractor_count,
                update_count=args.update_count,
                titan_dim=args.titan_dim,
                top_k=args.top_k,
            ),
        )
        print("MEMORIX_DYNAMIC_MEMORY_CAMPAIGN_OK")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    report = validate_dynamic_report(Path(args.report))
    print("MEMORIX_DYNAMIC_MEMORY_CAMPAIGN_VALID")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
