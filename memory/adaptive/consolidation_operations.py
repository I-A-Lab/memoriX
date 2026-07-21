"""Controlled consolidation lifecycle, scheduling, and recovery."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json, os, tempfile
from datetime import datetime, timezone
from memory.adaptive.consolidation_planning import MemoryConsolidationAction, collect_memory_consolidation_candidates, plan_memory_consolidation
from memory.data.paths import MemoryStoragePaths

@dataclass(frozen=True, slots=True)
class MemoryConsolidationOperationResult:
    action: str; ok: bool; message: str; session_id: str|None=None; plan_id: str|None=None
    status: str|None=None; registry_modified: bool=False; hot_site_modified: bool=False
    cold_site_modified: bool=False; runtime_modified: bool=False; consolidation_executed: bool=False
    memory_promoted: bool=False; memory_demoted: bool=False; memory_archived: bool=False
    memories_updated: int=0; memories_archived: int=0; groups_applied: int=0; groups_skipped: int=0
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


def _all_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _approved_plan_payload(plans: Path, plan_id: str) -> dict[str, Any] | None:
    records = [record for record in _all_jsonl(plans) if record.get("plan_id") == plan_id]
    if not records or records[-1].get("status") != "approved":
        return None
    return next((record.get("plan") for record in records if isinstance(record.get("plan"), dict)), None)


def _execute_plan_data(runtime_root: str | Path, plan: dict[str, Any], *, session_id: str, actor: str) -> tuple[int, int, int, int]:
    paths = MemoryStoragePaths.from_runtime_root(runtime_root)
    latest: dict[str, dict[str, Any]] = {}
    for record in _all_jsonl(paths.titan_metadata):
        memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
        if memory_id:
            latest[memory_id] = record
    archive_path = paths.runtime_root / "cold_site" / "consolidated_memories.jsonl"
    updated = archived = applied = skipped = 0
    for group in plan.get("groups", []):
        action = str(group.get("recommended_action", ""))
        memory_ids = [str(value) for value in group.get("memory_ids", []) if str(value)]
        if action not in {MemoryConsolidationAction.MARK_AS_DUPLICATE.value, MemoryConsolidationAction.SUPERSEDE_OLDER_MEMORY.value, MemoryConsolidationAction.ARCHIVE_INACTIVE.value} or len(memory_ids) < 1:
            skipped += 1
            continue
        survivor = memory_ids[-1]
        targets = memory_ids[:-1] if action != MemoryConsolidationAction.ARCHIVE_INACTIVE.value else memory_ids
        changed = False
        for memory_id in targets:
            record = latest.get(memory_id)
            if record is None:
                continue
            now = datetime.now(timezone.utc).isoformat()
            _append(archive_path, {"schema_version": 1, "memory_id": memory_id, "source_record": record, "consolidation_session_id": session_id, "consolidated_by": actor, "archived_at": now, "action": action})
            archived += 1
            if bool(record.get("active", True)):
                metadata = dict(record.get("metadata") or {})
                metadata.update({"consolidated_at": now, "consolidation_session_id": session_id, "consolidation_action": action, "consolidated_into_memory_id": survivor if memory_id != survivor else None})
                updated_record = {**record, "memory_id": memory_id, "active": False, "updated_at": now, "metadata": metadata}
                _append(paths.titan_metadata, updated_record)
                latest[memory_id] = updated_record
                updated += 1
            changed = True
        if changed:
            applied += 1
        else:
            skipped += 1
    return updated, archived, applied, skipped

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
    plan_payload=_approved_plan_payload(plans,plan_id)
    if plan_payload is None: raise ValueError('Consolidation plan must be approved.')
    current=_read_json(state,{})
    if current.get('active_session_id'): raise ValueError('A consolidation session is already active.')
    started_at=datetime.now(timezone.utc).isoformat()
    _atomic(state,{'active_session_id':session_id,'last_status':'running','last_started_at':started_at,'failure_count':current.get('failure_count',0)})
    _append(sessions,{'session_id':session_id,'plan_id':plan_id,'status':'running','actor':actor,'reason':reason,'validation_id':validation_id,'started_at':started_at})
    try:
        updated,archived,applied,skipped=_execute_plan_data(runtime_root,plan_payload,session_id=session_id,actor=actor)
    except Exception as error:
        _append(sessions,{'session_id':session_id,'plan_id':plan_id,'status':'failed','error':str(error),'failed_at':datetime.now(timezone.utc).isoformat()})
        _atomic(state,{'active_session_id':None,'last_status':'failed','failure_count':current.get('failure_count',0)+1,'last_session_id':session_id})
        raise
    completed_at=datetime.now(timezone.utc).isoformat()
    _append(sessions,{'session_id':session_id,'plan_id':plan_id,'status':'completed','completed_at':completed_at,'memories_updated':updated,'memories_archived':archived,'groups_applied':applied,'groups_skipped':skipped})
    _atomic(state,{'active_session_id':None,'last_status':'completed','last_completed_at':completed_at,'failure_count':current.get('failure_count',0),'last_session_id':session_id})
    return MemoryConsolidationOperationResult('execute',True,'completed',session_id=session_id,plan_id=plan_id,status='completed',registry_modified=True,runtime_modified=bool(updated or archived),hot_site_modified=bool(updated),cold_site_modified=bool(archived),consolidation_executed=True,memory_archived=bool(archived),memories_updated=updated,memories_archived=archived,groups_applied=applied,groups_skipped=skipped)

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
