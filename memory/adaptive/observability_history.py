"""Persistent observability snapshots, alerts, drift, and period comparison."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json, os, tempfile
from memory.adaptive.observability import (
    MemoryObservabilityCollection,
    MemoryObservabilityReport,
    MemoryObservabilityStatus,
    build_memory_observability_report,
    collect_memory_observability_samples,
)

@dataclass(frozen=True, slots=True)
class MemoryDriftSignal:
    metric_name: str
    baseline_value: float
    current_value: float
    absolute_delta: float
    relative_delta: float | None
    severity: str
    threshold: float
    direction: str
    explanation: str
    def to_dict(self)->dict[str,Any]: return {k:getattr(self,k) for k in self.__dataclass_fields__}

@dataclass(frozen=True, slots=True)
class MemoryPeriodComparison:
    baseline_snapshot_id: str
    current_snapshot_id: str
    signals: tuple[MemoryDriftSignal,...]
    improved_metric_names: tuple[str,...]
    regressed_metric_names: tuple[str,...]
    stable_metric_names: tuple[str,...]
    insufficient_data: bool
    dry_run: bool=True
    runtime_modified: bool=False
    policy_modified: bool=False
    neural_model_loaded: bool=False
    def to_dict(self)->dict[str,Any]:
        d={k:getattr(self,k) for k in self.__dataclass_fields__}
        d['signals']=[x.to_dict() for x in self.signals]
        return d

@dataclass(frozen=True, slots=True)
class MemoryObservabilityOperationResult:
    action: str
    ok: bool
    message: str
    snapshot_id: str|None=None
    alert_id: str|None=None
    snapshot_saved: bool=False
    alert_saved: bool=False
    alert_acknowledged: bool=False
    registry_modified: bool=False
    runtime_modified: bool=False
    hot_site_modified: bool=False
    cold_site_modified: bool=False
    policy_modified: bool=False
    neural_model_loaded: bool=False
    payload: dict[str,Any]|None=None
    def to_dict(self)->dict[str,Any]: return {k:getattr(self,k) for k in self.__dataclass_fields__}

def _paths(root:str|Path):
    d=Path(root)/'observability'
    return d,d/'snapshots.jsonl',d/'alerts.jsonl',d/'state.json'

def _append(path:Path,payload:dict[str,Any]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f: f.write(json.dumps(payload,ensure_ascii=False,sort_keys=True)+'\n')

def _atomic(path:Path,payload:dict[str,Any]):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent); os.close(fd)
    Path(tmp).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def _read_json(path:Path,default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (json.JSONDecodeError,OSError): return default

def _read_jsonl(path:Path)->list[dict[str,Any]]:
    out=[]
    if not path.exists(): return out
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        try:
            value=json.loads(line)
            if isinstance(value,dict): out.append(value)
        except json.JSONDecodeError: continue
    return out

def inspect_memory_observability_state(runtime_root:str|Path)->dict[str,Any]:
    d,snapshots,alerts,state=_paths(runtime_root)
    return {'registry_exists':d.exists(),'state':_read_json(state,{}),'snapshot_count':len(_read_jsonl(snapshots)),'alert_count':len(_read_jsonl(alerts)),'runtime_modified':False,'neural_model_loaded':False}

def list_memory_observability_snapshots(runtime_root:str|Path, *, limit:int=20)->tuple[dict[str,Any],...]:
    if limit<0: raise ValueError('limit must be non-negative')
    _,snapshots,_,_=_paths(runtime_root)
    return tuple(_read_jsonl(snapshots)[-limit:] if limit else [])

def list_memory_observability_alerts(runtime_root:str|Path, *, active_only:bool=True, limit:int=100)->tuple[dict[str,Any],...]:
    _,_,alerts,_=_paths(runtime_root); records=_read_jsonl(alerts)
    latest={}
    for record in records:
        alert_id=str(record.get('alert_id',''))
        if alert_id: latest[alert_id]=record
    values=list(latest.values())
    if active_only: values=[x for x in values if not x.get('acknowledged',False)]
    return tuple(values[-max(limit,0):])

def save_memory_observability_snapshot(runtime_root:str|Path, *, snapshot_id:str, report:MemoryObservabilityReport|None=None, actor:str='manual')->MemoryObservabilityOperationResult:
    if not snapshot_id.strip(): raise ValueError('snapshot_id is required')
    d,snapshots,alerts,state=_paths(runtime_root)
    existing={str(x.get('snapshot_id')) for x in _read_jsonl(snapshots)}
    if snapshot_id in existing: return MemoryObservabilityOperationResult('snapshot',True,'existing_snapshot_reused',snapshot_id=snapshot_id,payload=next(x for x in _read_jsonl(snapshots) if str(x.get('snapshot_id'))==snapshot_id))
    if report is None:
        report=build_memory_observability_report(collect_memory_observability_samples(runtime_root))
    now=datetime.now(timezone.utc).isoformat()
    payload={'snapshot_id':snapshot_id,'recorded_at':now,'actor':actor,'report':report.to_dict()}
    _append(snapshots,payload)
    active_alert_ids=[]
    for index, alert in enumerate(report.alerts,1):
        alert_id=f'{snapshot_id}:alert:{index}'
        active_alert_ids.append(alert_id)
        _append(alerts,{'alert_id':alert_id,'snapshot_id':snapshot_id,'acknowledged':False,'recorded_at':now,'alert':alert.to_dict()})
    _atomic(state,{'last_snapshot_id':snapshot_id,'last_snapshot_at':now,'last_health_status':report.status.value,'active_alert_ids':active_alert_ids,'updated_at':now})
    return MemoryObservabilityOperationResult('snapshot',True,'snapshot_saved',snapshot_id=snapshot_id,snapshot_saved=True,alert_saved=bool(active_alert_ids),registry_modified=True,payload=payload)

def acknowledge_memory_observability_alert(runtime_root:str|Path, *, alert_id:str, actor:str, reason:str)->MemoryObservabilityOperationResult:
    d,snapshots,alerts,state=_paths(runtime_root)
    latest={str(x.get('alert_id')):x for x in _read_jsonl(alerts)}
    if alert_id not in latest: raise ValueError('Unknown observability alert.')
    if latest[alert_id].get('acknowledged'): return MemoryObservabilityOperationResult('acknowledge',True,'already_acknowledged',alert_id=alert_id)
    now=datetime.now(timezone.utc).isoformat(); record={**latest[alert_id],'acknowledged':True,'acknowledged_at':now,'acknowledged_by':actor,'reason':reason}
    _append(alerts,record)
    current=_read_json(state,{})
    active=[x for x in current.get('active_alert_ids',[]) if x!=alert_id]
    _atomic(state,{**current,'active_alert_ids':active,'updated_at':now})
    return MemoryObservabilityOperationResult('acknowledge',True,'alert_acknowledged',alert_id=alert_id,alert_acknowledged=True,registry_modified=True)

def _snapshot_metrics(snapshot:dict[str,Any])->dict[str,float]:
    report=snapshot.get('report',{}) if isinstance(snapshot,dict) else {}
    values={}
    for indicator in report.get('indicators',[]) if isinstance(report,dict) else []:
        if isinstance(indicator,dict):
            name=str(indicator.get('indicator_name') or indicator.get('name') or indicator.get('category') or '')
            value=indicator.get('score')
            if name and isinstance(value,(int,float)): values[name]=float(value)
    score=report.get('overall_health_score') if isinstance(report,dict) else None
    if isinstance(score,(int,float)): values['overall_health_score']=float(score)
    return values

def compare_memory_observability_snapshots(baseline:dict[str,Any], current:dict[str,Any], *, threshold:float=0.10)->MemoryPeriodComparison:
    b=_snapshot_metrics(baseline); c=_snapshot_metrics(current); names=sorted(set(b)&set(c)); signals=[]; improved=[]; regressed=[]; stable=[]
    for name in names:
        delta=c[name]-b[name]; rel=None if b[name]==0 else delta/abs(b[name])
        if delta>threshold: direction='improved'; severity='healthy'; improved.append(name)
        elif delta<-threshold: direction='regressed'; severity='warning' if delta>-0.25 else 'critical'; regressed.append(name)
        else: direction='stable'; severity='info'; stable.append(name)
        signals.append(MemoryDriftSignal(name,b[name],c[name],delta,rel,severity,threshold,direction,f'{name} changed by {delta:.3f}'))
    return MemoryPeriodComparison(str(baseline.get('snapshot_id','baseline')),str(current.get('snapshot_id','current')),tuple(signals),tuple(improved),tuple(regressed),tuple(stable),not bool(names))

def detect_memory_observability_drift(runtime_root:str|Path, *, baseline_snapshot_id:str|None=None, current_snapshot_id:str|None=None, threshold:float=0.10)->MemoryPeriodComparison:
    snapshots=list(list_memory_observability_snapshots(runtime_root,limit=1000))
    if len(snapshots)<2: return MemoryPeriodComparison(baseline_snapshot_id or 'baseline',current_snapshot_id or 'current',(),(),(),(),True)
    def pick(identifier,default):
        if identifier is None: return default
        for item in snapshots:
            if item.get('snapshot_id')==identifier: return item
        raise ValueError(f'Unknown snapshot: {identifier}')
    return compare_memory_observability_snapshots(pick(baseline_snapshot_id,snapshots[-2]),pick(current_snapshot_id,snapshots[-1]),threshold=threshold)
