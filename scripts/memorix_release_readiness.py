#!/usr/bin/env python3
"""Print the final read-only memoriX release-readiness report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.data.paths import resolve_default_runtime_root
from memory.release import inspect_release_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--runtime-root", default=str(resolve_default_runtime_root()))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = inspect_release_readiness(args.project_root, args.runtime_root)
    print(json.dumps(report.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
