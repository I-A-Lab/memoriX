
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

PROJECT_ROOT=find_repository_root(Path(__file__))
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from memory.benchmark.topic_blocks import run_topic_block_benchmark

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repetitions",type=int,default=2)
    parser.add_argument("--output")
    parser.add_argument("--pretty",action="store_true")
    args=parser.parse_args()
    payload=run_topic_block_benchmark(repetitions=args.repetitions)
    text=json.dumps(payload,indent=2 if args.pretty else None,sort_keys=True)
    if args.output: Path(args.output).write_text(text+"\n",encoding="utf-8")
    print(text)
if __name__=="__main__": main()
