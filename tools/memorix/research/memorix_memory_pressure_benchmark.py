#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT=find_repository_root(Path(__file__))
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from memory.benchmark import DEFAULT_PRESSURE_SCENARIOS,run_memory_pressure_benchmark
from memory.data.paths import DEFAULT_RUNTIME_ROOT

def main(argv=None):
    parser=argparse.ArgumentParser(description="Run bounded synthetic memoriX memory-pressure benchmarks.")
    parser.add_argument("--runtime-root",default=str(DEFAULT_RUNTIME_ROOT)); parser.add_argument("--repetitions",type=int,default=3); parser.add_argument("--assessment-limit",type=int,default=1); parser.add_argument("--scenarios",type=int,nargs="+",default=list(DEFAULT_PRESSURE_SCENARIOS)); parser.add_argument("--output"); parser.add_argument("--pretty",action="store_true")
    args=parser.parse_args(argv)
    try: payload=run_memory_pressure_benchmark(runtime_root=args.runtime_root,scenarios=args.scenarios,repetitions=args.repetitions,assessment_limit=args.assessment_limit)
    except (TypeError,ValueError) as error: print(json.dumps({"status":"validation_failed","message":str(error)},sort_keys=True),file=sys.stderr); return 2
    text=json.dumps(payload,ensure_ascii=False,indent=2 if args.pretty else None,sort_keys=True,separators=None if args.pretty else (",",":"))
    if args.output: Path(args.output).write_text(text+"\n",encoding="utf-8")
    print(text); return 0
if __name__=="__main__": raise SystemExit(main())
