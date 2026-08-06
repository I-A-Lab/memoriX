#!/usr/bin/env python3
"""Dry-run adaptive-routing CLI."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT = find_repository_root(Path(__file__))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from memory.adaptive import inspect_runtime_adaptive_routing
from memory.data.paths import DEFAULT_RUNTIME_ROOT

def build_parser():
    p=argparse.ArgumentParser(description="Build a non-applied adaptive-routing plan.")
    p.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    p.add_argument("--target-id", required=True)
    p.add_argument("--retention-score", type=float, default=0.5)
    p.add_argument("--importance", type=float, default=0.5)
    p.add_argument("--confidence", type=float, default=0.5)
    p.add_argument("--surprise", type=float, default=0.0)
    p.add_argument("--protected", action="store_true")
    p.add_argument("--pinned", action="store_true")
    p.add_argument("--not-human-validated", action="store_true")
    p.add_argument("--required-slots", type=int, default=1)
    p.add_argument("--configured-capacity", type=int, default=50000)
    p.add_argument("--assessment-limit", type=int, default=100)
    p.add_argument("--simulate-memory-count", type=int)
    p.add_argument("--pretty", action="store_true")
    return p

def main(argv=None):
    a=build_parser().parse_args(argv)
    try:
        report=inspect_runtime_adaptive_routing(runtime_root=a.runtime_root,target_id=a.target_id,retention_score=a.retention_score,importance=a.importance,confidence=a.confidence,surprise=a.surprise,protected=a.protected,pinned=a.pinned,human_validated=not a.not_human_validated,required_slots=a.required_slots,configured_capacity=a.configured_capacity,assessment_limit=a.assessment_limit,simulated_memory_count=a.simulate_memory_count)
    except (TypeError,ValueError) as e:
        print(json.dumps({"status":"validation_failed","message":str(e)},sort_keys=True),file=sys.stderr); return 2
    print(json.dumps(report.to_dict(),indent=2 if a.pretty else None,sort_keys=True,separators=None if a.pretty else (",",":")))
    return 0
if __name__=="__main__": raise SystemExit(main())
