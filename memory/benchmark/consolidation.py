from __future__ import annotations
import time
from typing import Any
from memory.adaptive import MemoryConsolidationCandidate, detect_memory_consolidation_groups

def run_consolidation_benchmark(sizes=(100,1000,10000))->dict[str,Any]:
 results=[]
 for size in sizes:
  candidates=tuple(MemoryConsolidationCandidate(str(i),f'memory topic {i//2}',True,None,None,'block',(),None,None,None,None,False,{}) for i in range(size))
  started=time.perf_counter(); groups=detect_memory_consolidation_groups(candidates[:min(size,500)])
  results.append({'memory_count':size,'sampled_count':min(size,500),'group_count':len(groups),'duration_ms':round((time.perf_counter()-started)*1000,3)})
 return {'results':results,'synthetic_data_only':True,'dry_run':True,'cold_site_accessed':False,'neural_model_loaded':False}
