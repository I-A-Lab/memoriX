from __future__ import annotations
import time
from typing import Any
from memory.adaptive import MemoryMetricSample, MemoryMetricWindow, MemoryObservabilityCollection, build_memory_observability_report

def run_observability_benchmark(sizes=(100,10000,100000))->dict[str,Any]:
    results=[]
    for size in sizes:
        sample_count=min(size,1000)
        samples=tuple(MemoryMetricSample(f'metric_{i}',(i%100)/100,'ratio','synthetic',sample_count=1) for i in range(sample_count))
        collection=MemoryObservabilityCollection(samples=samples,window=MemoryMetricWindow(None,None,sample_count,1,sample_count*64),files_inspected=1,bytes_inspected=sample_count*64,sources_used=('synthetic',),source_records=(('synthetic',size),),malformed_record_count=0,truncated=size>sample_count,dry_run=True)
        started=time.perf_counter(); report=build_memory_observability_report(collection)
        results.append({'event_count':size,'sampled_count':sample_count,'duration_ms':round((time.perf_counter()-started)*1000,3),'alert_count':len(report.alerts)})
    return {'results':results,'synthetic_data_only':True,'dry_run':True,'cold_site_accessed':False,'neural_model_loaded':False}
