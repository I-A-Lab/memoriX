
from __future__ import annotations
import json, time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from memory.adaptive import inspect_memory_policy_registry, search_memory_policies, propose_memory_policy

def run_policy_lifecycle_benchmark(*, counts=(10,100,1000), repetitions=1) -> dict[str, Any]:
    results=[]
    for count in counts:
        timings=[]
        for _ in range(repetitions):
            with TemporaryDirectory() as temporary:
                root=Path(temporary); policies=root/"policies"; policies.mkdir(parents=True)
                candidate=search_memory_policies().best_policy.to_dict()
                line=json.dumps({"version_id":"x","policy":candidate,"status":"proposed","created_at":"2026-07-20T00:00:00+00:00","created_by":"benchmark","source":"synthetic","parent_version_id":None,"metrics":None})
                (policies/"policy_versions.jsonl").write_text("\n".join(line.replace('"x"',f'"v{i}"',1) for i in range(count))+"\n",encoding="utf-8")
                (policies/"policy_state.json").write_text(json.dumps({"active_policy_version_id":None,"previous_policy_version_id":None,"pending_proposal_ids":[]}),encoding="utf-8")
                start=time.perf_counter(); snapshot=inspect_memory_policy_registry(root); timings.append(time.perf_counter()-start)
                assert len(snapshot.versions)==count
        results.append({"version_count":count,"mean_seconds":sum(timings)/len(timings)})
    return {"results":results,"synthetic_data_only":True,"neural_model_loaded":False,"cold_site_accessed":False}
