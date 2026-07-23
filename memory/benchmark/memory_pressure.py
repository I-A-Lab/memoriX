"""Bounded synthetic benchmark for memory-pressure diagnostics."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable
from memory.adaptive import inspect_runtime_memory_pressure

DEFAULT_PRESSURE_SCENARIOS=(10_000,100_000,1_000_000,6_000_000)

@dataclass(frozen=True, slots=True)
class MemoryPressureBenchmarkResult:
    simulated_memory_count:int
    elapsed_ms:float
    mean_pressure:float
    maximum_pressure:float
    pruning_candidate_count:int
    assessment_count:int
    runtime_modified:bool=False
    cold_site_accessed:bool=False
    neural_model_loaded:bool=False
    def to_dict(self)->dict[str,Any]: return asdict(self)

def run_memory_pressure_benchmark(*,runtime_root:str|Path,scenarios:Iterable[int]=DEFAULT_PRESSURE_SCENARIOS,repetitions:int=3,assessment_limit:int=1)->dict[str,Any]:
    if repetitions<=0: raise ValueError("repetitions must be positive.")
    results=[]
    for count in scenarios:
        if count<0: raise ValueError("scenarios must be non-negative.")
        durations=[]; report=None
        for _ in range(repetitions):
            start=perf_counter(); report=inspect_runtime_memory_pressure(runtime_root=runtime_root,simulated_memory_count=count,assessment_limit=assessment_limit); durations.append((perf_counter()-start)*1000.0)
        assert report is not None
        results.append(MemoryPressureBenchmarkResult(simulated_memory_count=count,elapsed_ms=sum(durations)/len(durations),mean_pressure=report.snapshot.mean_pressure,maximum_pressure=report.snapshot.maximum_pressure,pruning_candidate_count=report.snapshot.pruning_candidate_count,assessment_count=len(report.snapshot.assessments)).to_dict())
    return {"status":"ok","synthetic_data_only":True,"actions_applied":False,"runtime_modified":False,"cold_site_accessed":False,"neural_model_loaded":False,"repetitions":repetitions,"assessment_limit":assessment_limit,"results":results}
