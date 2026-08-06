#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.data.paths import DEFAULT_RUNTIME_ROOT
from memory.sync.nightly_runner import EXIT_VALIDATION, NightlyRunner


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description='Run protected memoriX nightly consolidation.')
    result.add_argument('--runtime-root', default=str(DEFAULT_RUNTIME_ROOT))
    mode = result.add_mutually_exclusive_group()
    mode.add_argument('--clear-after-success', action='store_true')
    mode.add_argument('--keep-short-term', action='store_true')
    result.add_argument('--trigger', choices=('manual','task_scheduler','opencode'), default='manual')
    result.add_argument('--lock-timeout-hours', type=float, default=6)
    result.add_argument('--pretty', action='store_true')
    result.add_argument('--compact', action='store_true')
    result.add_argument('--status-only', action='store_true')
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        runner = NightlyRunner(args.runtime_root, lock_timeout_hours=args.lock_timeout_hours)
        if args.status_only:
            payload = runner.latest_status()
            result = {'status': 'never_run'} if payload is None else payload
            print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True, separators=None if args.pretty else (',', ':')))
            return 0
        clear = not args.keep_short_term
        result = runner.run(clear_short_term_after_success=clear, trigger=args.trigger)
        print(json.dumps(result.payload, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True, separators=None if args.pretty else (',', ':')))
        return result.exit_code
    except (TypeError, ValueError) as exc:
        print(json.dumps({'status':'validation_failed','message':str(exc)}, ensure_ascii=False), file=sys.stderr)
        return EXIT_VALIDATION

if __name__ == '__main__':
    raise SystemExit(main())
