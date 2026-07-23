
from __future__ import annotations
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any
from memory.adaptive import create_memory_topic_block, plan_memory_topic_block_rebalance

def run_topic_block_benchmark(*, block_counts=(10,100,1000), repetitions=2) -> dict[str, Any]:
    results=[]
    for count in block_counts:
        timings=[]
        with tempfile.TemporaryDirectory() as directory:
            for index in range(count):
                create_memory_topic_block(directory, canonical_topic=f"topic-{index}")
            for _ in range(repetitions):
                started=time.perf_counter()
                report=plan_memory_topic_block_rebalance(directory)
                timings.append((time.perf_counter()-started)*1000)
            results.append({"block_count":count,"median_ms":statistics.median(timings),"recommendations":list(report.recommendations)})
    return {"results":results,"synthetic_data_only":True,"dry_run":True,"runtime_modified":False,"cold_site_accessed":False,"neural_model_loaded":False}
