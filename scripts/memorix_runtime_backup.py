#!/usr/bin/env python3
"""Create and verify one portable memoriX runtime backup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.release import create_runtime_backup, inspect_runtime_backup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root")
    parser.add_argument("destination")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    create_runtime_backup(args.runtime_root, args.destination)
    manifest = inspect_runtime_backup(args.destination)
    print(json.dumps(manifest.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
