#!/usr/bin/env python3
"""Run the isolated final QuickTemp smoke scenario."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.release import run_demo_smoke


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = run_demo_smoke(args.runtime_root)
    print(json.dumps(report.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
