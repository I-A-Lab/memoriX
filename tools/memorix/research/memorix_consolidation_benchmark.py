from pathlib import Path
import argparse,json,sys
MEMORIX_TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(MEMORIX_TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(MEMORIX_TOOLS_ROOT))

from _repository import find_repository_root

ROOT=find_repository_root(Path(__file__))
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from memory.benchmark.consolidation import run_consolidation_benchmark
p=argparse.ArgumentParser(); p.add_argument('--output'); p.add_argument('--pretty',action='store_true'); args=p.parse_args()
payload=run_consolidation_benchmark(); text=json.dumps(payload,indent=2 if args.pretty else None)
if args.output: Path(args.output).write_text(text+'\n',encoding='utf-8')
print(text)
