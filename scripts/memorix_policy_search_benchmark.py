#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))
from memory.benchmark import run_policy_search_benchmark

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--runtime-root", required=True); parser.add_argument("--repetitions", type=int, default=3); parser.add_argument("--output"); parser.add_argument("--pretty", action="store_true"); args=parser.parse_args(argv)
    payload=run_policy_search_benchmark(runtime_root=args.runtime_root, repetitions=args.repetitions).to_dict(); text=json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True); print(text)
    if args.output: Path(args.output).write_text(text+"\n", encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
