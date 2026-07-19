"""Bounded synthetic benchmark for adaptive routing."""
from __future__ import annotations
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
from memory.adaptive import inspect_runtime_adaptive_routing

DEFAULT_ROUTING_SCENARIOS=(10_000,100_000,1_000_000,6_000_000)

def run_adaptive_routing_benchmark(*,runtime_root:str|Path,scenarios:Iterable[int]=DEFAULT_ROUTING_SCENARIOS,repetitions:int=3)->dict[str,Any]:
    if repetitions<=0: raise ValueError("repetitions must be positive.")
    results=[]
    for count in scenarios:
        durations=[]; report=None
        for _ in range(repetitions):
            start=perf_counter(); report=inspect_runtime_adaptive_routing(runtime_root=runtime_root,target_id=f"candidate-{count}",retention_score=0.9,importance=0.9,confidence=0.9,configured_capacity=50_000,assessment_limit=1,simulated_memory_count=count); durations.append((perf_counter()-start)*1000)
        results.append({"simulated_memory_count":count,"elapsed_ms":sum(durations)/len(durations),"decision":report.plan.decision.decision.value})
    return {"status":"ok","synthetic_data_only":True,"dry_run":True,"runtime_modified":False,"cold_site_accessed":False,"neural_model_loaded":False,"results":results}
