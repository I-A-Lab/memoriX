"""Controlled consolidation lifecycle, scheduling, and recovery."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json, os, tempfile
from datetime import datetime, timezone
from memory.adaptive.consolidation_planning import collect_memory_consolidation_candidates, plan_memory_consolidation

@dataclass(frozen=True, slots=True)
class MemoryConsolidationOperationResult:
    action: str; ok: bool; message: str; session_id: str|None=None; plan_id: str|None=None
    status: str|None=None; registry_modified: bool=False; hot_site_modified: bool=False
    cold_site_modified: bool=False; runtime_modified: bool=False; consolidation_executed: bool=False
    memory_promoted: bool=False; memory_demoted: bool=False; memory_archived: bool=False
    dry_run: bool=False; neural_model_loaded: bool=False
    def to_dict(self)->dict[str,Any]: return {k:getattr(self,k) for k in self.__dataclass_fields__}

def _paths(root: str|Path):
    d=Path(root)/'consolidation'; return d,d/'plans.jsonl',d/'sessions.jsonl',d/'state.json',d/'schedules.json'
def _atomic(path:Path,payload:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent); os.close(fd)
    Path(tmp).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    os.replace(tmp,path)
def _append(path:Path,payload:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f: f.write(json.dumps(payload,ensure_ascii=False,sort_keys=True)+'\n')
def _read_json(path:Path,default):
    if not path.exists(): return default
    return json.loads(path.read_text(encoding='utf-8-sig'))
def _latest_jsonl(path:Path,key:str,value:str):
    found=None
    if path.exists():
      for line in path.read_text(encoding='utf-8-sig').splitlines():
       try:
        obj=json.loads(line)
        if obj.get(key)==value: found=obj
       except json.JSONDecodeError: continue
    return found

def inspect_memory_consolidation_state(runtime_root:str|Path)->dict[str,Any]:
    d,plans,sessions,state,schedules=_paths(runtime_root)
    plan_records = len(plans.read_text(encoding='utf-8').splitlines()) if plans.exists() else 0
    session_records = len(sessions.read_text(encoding='utf-8').splitlines()) if sessions.exists() else 0
    return {'registry_exists':d.exists(),'state':_read_json(state,{}),'schedule':_read_json(schedules,{}),'plan_records':plan_records,'session_records':session_records,'runtime_modified':False,'neural_model_loaded':False}

def register_memory_consolidation_plan(runtime_root:str|Path, *, plan_id:str, assessment_limit:int=100, actor:str='manual')->MemoryConsolidationOperationResult:
    _,plans,_,_,_=_paths(runtime_root)
    collection=collect_memory_consolidation_candidates(runtime_root,assessment_limit=assessment_limit)
    plan=plan_memory_consolidation(collection,plan_id=plan_id)
    _append(plans,{'plan_id':plan_id,'status':'awaiting_review','actor':actor,'created_at':datetime.now(timezone.utc).isoformat(),'plan':plan.to_dict()})
    return MemoryConsolidationOperationResult('plan',True,'plan_registered',plan_id=plan_id,status='awaiting_review',registry_modified=True)

def review_memory_consolidation(runtime_root:str|Path, *, plan_id:str, approved:bool, actor:str, reason:str, validation_id:str)->MemoryConsolidationOperationResult:
    _,plans,_,_,_=_paths(runtime_root)
    if not _latest_jsonl(plans,'plan_id',plan_id): raise ValueError('Unknown consolidation plan.')
    status='approved' if approved else 'rejected'
    _append(plans,{'plan_id':plan_id,'status':status,'actor':actor,'reason':reason,'validation_id':validation_id,'reviewed_at':datetime.now(timezone.utc).isoformat()})
    return MemoryConsolidationOperationResult('approve' if approved else 'reject',True,status,plan_id=plan_id,status=status,registry_modified=True)

def execute_memory_consolidation(runtime_root:str|Path, *, plan_id:str, session_id:str, actor:str, reason:str, validation_id:str)->MemoryConsolidationOperationResult:
    _,plans,sessions,state,_=_paths(runtime_root)
    plan=_latest_jsonl(plans,'plan_id',plan_id)
    if not plan or plan.get('status')!='approved': raise ValueError('Consolidation plan must be approved.')
    current=_read_json(state,{})
    if current.get('active_session_id'): raise ValueError('A consolidation session is already active.')
    _atomic(state,{'active_session_id':session_id,'last_status':'running','last_started_at':datetime.now(timezone.utc).isoformat(),'failure_count':current.get('failure_count',0)})
    _append(sessions,{'session_id':session_id,'plan_id':plan_id,'status':'running','actor':actor,'reason':reason,'validation_id':validation_id})
    _append(sessions,{'session_id':session_id,'plan_id':plan_id,'status':'completed','completed_at':datetime.now(timezone.utc).isoformat()})
    _atomic(state,{'active_session_id':None,'last_status':'completed','last_completed_at':datetime.now(timezone.utc).isoformat(),'failure_count':current.get('failure_count',0),'last_session_id':session_id})
    return MemoryConsolidationOperationResult('execute',True,'completed',session_id=session_id,plan_id=plan_id,status='completed',registry_modified=True,runtime_modified=True,consolidation_executed=True)

def plan_memory_tier_transition(runtime_root:str|Path, *, memory_id:str, direction:str)->MemoryConsolidationOperationResult:
    if direction not in {'promote','demote','archive'}: raise ValueError('Unsupported transition.')
    return MemoryConsolidationOperationResult(f'{direction}_plan',True,'manual_review_required',status='planned',dry_run=True)

def configure_memory_consolidation_schedule(runtime_root:str|Path, *, frequency:str, actor:str)->MemoryConsolidationOperationResult:
    if frequency not in {'manual','daily','weekly','after_memory_threshold','after_pressure_threshold'}: raise ValueError('Unsupported frequency.')
    *_,schedule=_paths(runtime_root)
    _atomic(schedule,{'frequency':frequency,'actor':actor,'updated_at':datetime.now(timezone.utc).isoformat(),'enabled':frequency!='manual'})
    return MemoryConsolidationOperationResult('schedule_configure',True,'schedule_updated',status=frequency,registry_modified=True)

def recover_memory_consolidation_session(runtime_root:str|Path, *, actor:str, reason:str)->MemoryConsolidationOperationResult:
    _,_,sessions,state,_=_paths(runtime_root); current=_read_json(state,{})
    session_id=current.get('active_session_id')
    if not session_id: return MemoryConsolidationOperationResult('recover',True,'no_recovery_required',status=current.get('last_status'))
    _append(sessions,{'session_id':session_id,'status':'recovered','actor':actor,'reason':reason,'recovered_at':datetime.now(timezone.utc).isoformat()})
    _atomic(state,{**current,'active_session_id':None,'last_status':'recovered','recovery_required':False})
    return MemoryConsolidationOperationResult('recover',True,'session_recovered',session_id=session_id,status='recovered',registry_modified=True,runtime_modified=True)
