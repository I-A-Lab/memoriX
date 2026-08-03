from __future__ import annotations
import argparse, json, sys, tempfile
from pathlib import Path
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

ROOT=find_repository_root(Path(__file__))
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from memory.benchmark.dataset_generator import validate_dataset_directory
from memory.benchmark.memory_pure_benchmark import DeterministicLexicalEngine, MemoriXGatewayEngine, run_pure_memory_benchmark, write_results

def main()->int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run'); run.add_argument('--dataset',required=True); run.add_argument('--output',required=True); run.add_argument('--engine',choices=('lexical','memorix'),default='lexical'); run.add_argument('--runtime-root'); run.add_argument('--top-k',type=int,default=5)
    args=parser.parse_args(); dataset=Path(args.dataset).resolve(); artifact=validate_dataset_directory(dataset)
    if args.engine=='memorix':
        if not args.runtime_root: raise SystemExit('--runtime-root is required for engine=memorix.')
        engine=MemoriXGatewayEngine(Path(args.runtime_root).resolve())
    else: engine=DeterministicLexicalEngine()
    metrics,rows=run_pure_memory_benchmark(dataset,engine,top_k=args.top_k)
    report=write_results(Path(args.output),metrics,rows,engine_name=args.engine,dataset_id=artifact.dataset_id)
    print('MEMORIX_MEMORY_PURE_BENCHMARK_OK'); print(json.dumps({'report':str(report),'metrics':metrics.to_dict()},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
