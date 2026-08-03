from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REPOSITORY_ROOT = PROJECT_ROOT

from memory.benchmark.tenant_contradiction_audit import (
    PROFILE_SPECS,
    TenantAuditRequest,
    run_tenant_audit,
    validate_tenant_audit_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--output", required=True)
    run.add_argument("--archive", required=True)
    run.add_argument("--profile", choices=tuple(PROFILE_SPECS), default="quick")
    run.add_argument("--seeds", nargs="+", type=int)
    run.add_argument("--user-count", type=int)
    run.add_argument("--project-count", type=int)
    run.add_argument("--distractor-count", type=int)
    run.add_argument("--titan-dim", type=int)
    run.add_argument("--top-k", type=int)

    validate = commands.add_parser("validate")
    validate.add_argument("--report", required=True)

    args = parser.parse_args()
    if args.command == "run":
        report = run_tenant_audit(
            repository_root=REPOSITORY_ROOT,
            output_root=Path(args.output),
            archive_path=Path(args.archive),
            request=TenantAuditRequest(
                profile=args.profile,
                seeds=None if args.seeds is None else tuple(args.seeds),
                user_count=args.user_count,
                project_count=args.project_count,
                distractor_count=args.distractor_count,
                titan_dim=args.titan_dim,
                top_k=args.top_k,
            ),
        )
        print("MEMORIX_TENANT_CONTRADICTION_AUDIT_OK")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    report = validate_tenant_audit_report(Path(args.report))
    print("MEMORIX_TENANT_CONTRADICTION_AUDIT_VALID")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
