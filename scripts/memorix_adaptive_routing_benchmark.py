from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.benchmark import run_adaptive_routing_benchmark

def main()->int:
 p=argparse.ArgumentParser(); p.add_argument("--runtime-root",required=True); p.add_argument("--repetitions",type=int,default=3); p.add_argument("--output"); p.add_argument("--pretty",action="store_true"); a=p.parse_args(); payload=run_adaptive_routing_benchmark(runtime_root=a.runtime_root,repetitions=a.repetitions); text=json.dumps(payload,indent=2 if a.pretty else None,sort_keys=True); print(text);
 if a.output: Path(a.output).write_text(text+"\n",encoding="utf-8")
 return 0
if __name__=="__main__": raise SystemExit(main())
