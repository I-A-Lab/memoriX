
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

ROOT=find_repository_root(Path(__file__))
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from memory.benchmark import run_policy_lifecycle_benchmark
p=argparse.ArgumentParser(); p.add_argument("--repetitions",type=int,default=1); p.add_argument("--output"); p.add_argument("--pretty",action="store_true")
a=p.parse_args(); payload=run_policy_lifecycle_benchmark(repetitions=a.repetitions); text=json.dumps(payload,indent=2 if a.pretty else None,sort_keys=True)
if a.output: Path(a.output).write_text(text+"\n",encoding="utf-8")
print(text)
