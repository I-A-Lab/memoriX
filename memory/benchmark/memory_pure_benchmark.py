"""Pure-memory benchmark runner and deterministic retrieval metrics."""
from __future__ import annotations
import hashlib, json, math, time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

BENCHMARK_VERSION = "33.1"

class RetrievalEngine(Protocol):
    def ingest(self, records: Sequence[Mapping[str, Any]]) -> None: ...
    def retrieve(self, query: str, *, top_k: int) -> Sequence[Mapping[str, Any]]: ...

@dataclass(frozen=True, slots=True)
class PureMemoryMetrics:
    query_count:int; recall_at_1:float; recall_at_5:float; mean_reciprocal_rank:float
    forbidden_hit_rate:float; exact_value_rate:float; mean_retrieve_ms:float; p95_retrieve_ms:float
    def to_dict(self)->dict[str,Any]: return asdict(self)

class DeterministicLexicalEngine:
    """Small deterministic control engine used to validate the benchmark itself."""
    def __init__(self)->None: self._records:list[dict[str,Any]]=[]
    def ingest(self, records:Sequence[Mapping[str,Any]])->None:
        self._records=[dict(r) for r in records if bool(r.get('active')) and bool(r.get('should_retrieve'))]
    def retrieve(self, query:str, *, top_k:int)->Sequence[Mapping[str,Any]]:
        tokens=set(_tokens(query)); scored=[]
        for record in self._records:
            key=str((record.get('canonical_fact') or {}).get('key',''))
            hay=set(_tokens(str(record.get('content',''))+' '+key))
            score=len(tokens & hay)/max(1,len(tokens))
            scored.append((score,str(record['record_id']),record))
        scored.sort(key=lambda x:(-x[0],x[1]))
        return [dict(item[2], score=float(item[0])) for item in scored[:top_k]]

class MemoriXGatewayEngine:
    """Real memoriX hot-site adapter. Runtime must be outside the repository."""
    def __init__(self, runtime_root:Path)->None:
        from memory.data import MemoryStoragePaths
        from memory.gateway.public_api import MemoriXGateway
        self._gateway=MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(runtime_root), titan_top_k=5, titan_min_score=0.0)
    def ingest(self, records:Sequence[Mapping[str,Any]])->None:
        for record in records:
            if not bool(record.get('active')) or not bool(record.get('should_retrieve')): continue
            candidate=self._gateway.propose_memory_candidate(
                content=str(record['content']), reason='benchmark ingestion', source_event_ids=(str(record['record_id']),),
                importance=0.5, confidence=1.0, surprise=0.0,
                metadata={'benchmark_record_id':str(record['record_id']), 'canonical_fact':record.get('canonical_fact'), 'family':record.get('family')},
            )
            self._gateway.validate_memory_candidate(candidate.candidate_id, validated_by='benchmark', validation_reason='deterministic benchmark fixture')
    def retrieve(self, query:str, *, top_k:int)->Sequence[Mapping[str,Any]]:
        result=self._gateway.retrieve_memory(query, top_k=top_k)
        rows=[]
        for match in result.matches:
            rows.append({'record_id':str(match.metadata.get('benchmark_record_id','')), 'content':match.content, 'score':match.score, 'canonical_fact':match.metadata.get('canonical_fact')})
        return rows

def run_pure_memory_benchmark(dataset_dir:Path, engine:RetrievalEngine, *, top_k:int=5)->tuple[PureMemoryMetrics,list[dict[str,Any]]]:
    if top_k<1: raise ValueError('top_k must be positive.')
    records=_read_jsonl(dataset_dir/'records.jsonl'); queries=_read_jsonl(dataset_dir/'queries.jsonl')
    engine.ingest(records); rows=[]; latencies=[]
    for query in queries:
        started=time.perf_counter_ns(); matches=list(engine.retrieve(str(query['query']), top_k=top_k)); elapsed=(time.perf_counter_ns()-started)/1_000_000
        latencies.append(elapsed); ids=[str(m.get('record_id','')) for m in matches]
        expected=[str(v) for v in query.get('expected_record_ids',[])]; forbidden=[str(v) for v in query.get('forbidden_record_ids',[])]
        rank=next((i+1 for i,v in enumerate(ids) if v in expected),None)
        expected_value=query.get('expected_value'); exact=expected_value is None or any(str((m.get('canonical_fact') or {}).get('value'))==str(expected_value) for m in matches)
        rows.append({'query_id':query['query_id'],'family':query['family'],'expected_record_ids':expected,'forbidden_record_ids':forbidden,'retrieved_record_ids':ids,'rank':rank,'forbidden_hit':any(v in forbidden for v in ids),'exact_value':bool(exact),'retrieve_ms':elapsed})
    n=len(rows)
    if n==0: raise ValueError('Dataset has no queries.')
    metrics=PureMemoryMetrics(n, sum(r['rank']==1 for r in rows)/n, sum(r['rank'] is not None and r['rank']<=5 for r in rows)/n, sum(0 if r['rank'] is None else 1/r['rank'] for r in rows)/n, sum(r['forbidden_hit'] for r in rows)/n, sum(r['exact_value'] for r in rows)/n, sum(latencies)/n, _percentile(latencies,0.95))
    return metrics, rows

def write_results(output_dir:Path, metrics:PureMemoryMetrics, rows:Sequence[Mapping[str,Any]], *, engine_name:str, dataset_id:str)->Path:
    output_dir=output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()): raise FileExistsError(f'Refusing to overwrite non-empty result directory: {output_dir}')
    output_dir.mkdir(parents=True,exist_ok=True)
    query_path=output_dir/'query_results.jsonl'; query_path.write_text(''.join(json.dumps(dict(r),sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf-8',newline='\n')
    payload={'schema_version':1,'benchmark_version':BENCHMARK_VERSION,'engine':engine_name,'dataset_id':dataset_id,'metrics':metrics.to_dict(),'query_results_sha256':hashlib.sha256(query_path.read_bytes()).hexdigest()}
    path=output_dir/'memory_pure_report.json'; path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n'); return path

def _read_jsonl(path:Path)->list[dict[str,Any]]:
    if not path.is_file(): raise FileNotFoundError(str(path))
    rows=[]
    for number,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        value=json.loads(line)
        if not isinstance(value,dict): raise ValueError(f'JSONL line {number} must be an object.')
        rows.append(value)
    return rows

def _tokens(value:str)->list[str]:
    import re
    return re.findall(r'[a-z0-9_]+',value.lower())

def _percentile(values:Sequence[float], q:float)->float:
    ordered=sorted(values)
    if not ordered:return 0.0
    index=max(0,min(len(ordered)-1,math.ceil(q*len(ordered))-1)); return float(ordered[index])
