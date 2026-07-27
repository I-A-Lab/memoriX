"""Real memoriX contradiction and tenant-isolation audit.

This benchmark calls the public Python gateway and real Titan hot site. It does
not call an LLM, network provider, MCP, or OpenCode. It is diagnostic: the ZIP
is always produced when execution completes and source integrity is preserved,
even when strict tenant-isolation checks expose warnings.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import inspect
import json
import random
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

from memory.data import ForgetAction, MemoryStoragePaths
from memory.gateway import MemoriXGateway

SCHEMA_VERSION = 1
CAMPAIGN_VERSION = "42.1.0"

PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "quick": {
        "seeds": (101, 202),
        "user_count": 4,
        "project_count": 3,
        "distractor_count": 50,
        "titan_dim": 32,
        "top_k": 5,
    },
    "standard": {
        "seeds": (101, 202, 303),
        "user_count": 8,
        "project_count": 4,
        "distractor_count": 250,
        "titan_dim": 48,
        "top_k": 10,
    },
}

PROTECTED_PATHS = (
    Path("memory/gateway"),
    Path("memory/hot_site"),
    Path("memory/cold_site"),
    Path("memory/consolidation"),
    Path("memory/sync"),
    Path("memory/data"),
    Path("scripts/memorix_mcp_server.py"),
    Path("packages/opencode/src/memorix"),
    Path("packages/opencode/src/tool"),
    Path(".opencode/plugins/memorix.ts"),
)


@dataclass(frozen=True, slots=True)
class TenantAuditRequest:
    profile: str = "quick"
    seeds: tuple[int, ...] | None = None
    user_count: int | None = None
    project_count: int | None = None
    distractor_count: int | None = None
    titan_dim: int | None = None
    top_k: int | None = None

    def resolved(self) -> "ResolvedTenantAuditRequest":
        if self.profile not in PROFILE_SPECS:
            raise ValueError(
                "profile must be one of: " + ", ".join(PROFILE_SPECS)
            )
        spec = PROFILE_SPECS[self.profile]
        seeds = tuple(self.seeds or spec["seeds"])
        user_count = int(
            spec["user_count"] if self.user_count is None else self.user_count
        )
        project_count = int(
            spec["project_count"]
            if self.project_count is None
            else self.project_count
        )
        distractor_count = int(
            spec["distractor_count"]
            if self.distractor_count is None
            else self.distractor_count
        )
        titan_dim = int(
            spec["titan_dim"] if self.titan_dim is None else self.titan_dim
        )
        top_k = int(spec["top_k"] if self.top_k is None else self.top_k)
        if not seeds:
            raise ValueError("At least one seed is required.")
        if len(set(seeds)) != len(seeds):
            raise ValueError("Duplicate seeds are not allowed.")
        if user_count < 3:
            raise ValueError("user_count must be at least 3.")
        if project_count < 2:
            raise ValueError("project_count must be at least 2.")
        if distractor_count < 0:
            raise ValueError("distractor_count must be non-negative.")
        if titan_dim < 16:
            raise ValueError("titan_dim must be at least 16.")
        if top_k < 2:
            raise ValueError("top_k must be at least 2.")
        return ResolvedTenantAuditRequest(
            profile=self.profile,
            seeds=tuple(int(seed) for seed in seeds),
            user_count=user_count,
            project_count=project_count,
            distractor_count=distractor_count,
            titan_dim=titan_dim,
            top_k=top_k,
        )


@dataclass(frozen=True, slots=True)
class ResolvedTenantAuditRequest:
    profile: str
    seeds: tuple[int, ...]
    user_count: int
    project_count: int
    distractor_count: int
    titan_dim: int
    top_k: int


@dataclass(frozen=True, slots=True)
class AuditCheck:
    seed: int
    category: str
    scenario: str
    passed: bool
    duration_ms: float
    expected: str
    observed: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["details"] = dict(self.details)
        return payload


def _canonical_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_snapshot(repository_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for relative in PROTECTED_PATHS:
        target = repository_root / relative
        if target.is_file():
            snapshot[relative.as_posix()] = _hash_file(target)
            continue
        if not target.is_dir():
            continue
        for path in sorted(target.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            snapshot[path.relative_to(repository_root).as_posix()] = _hash_file(path)
    return snapshot


def compare_snapshots(
    before: Mapping[str, str], after: Mapping[str, str]
) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    return {
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": sorted(
            key
            for key in before_keys & after_keys
            if before[key] != after[key]
        ),
    }


def _make_gateway(
    paths: MemoryStoragePaths,
    request: ResolvedTenantAuditRequest,
    seed: int,
) -> MemoriXGateway:
    gc.collect()
    torch.manual_seed(seed)
    return MemoriXGateway(
        storage_paths=paths,
        titan_d_model=request.titan_dim,
        titan_hidden_dim=request.titan_dim,
        titan_max_items=max(500, request.distractor_count + 250),
        titan_device="cpu",
        titan_top_k=request.top_k,
        titan_min_score=0.0,
    )


def _validate_memory(
    gateway: MemoriXGateway,
    *,
    content: str,
    source_event_id: str,
    metadata: Mapping[str, Any],
    target_memory_id: str | None = None,
):
    candidate = gateway.propose_memory_candidate(
        content=content,
        reason="Part 42 tenant and contradiction audit.",
        source_event_ids=(source_event_id,),
        importance=0.98,
        confidence=1.0,
        surprise=0.8,
        target_memory_id=target_memory_id,
        metadata=dict(metadata),
    )
    return gateway.validate_memory_candidate(
        candidate.candidate_id,
        validated_by="part42_benchmark_reviewer",
        validation_reason="Approved for tenant-isolation audit.",
    )


def _top_id(result: Any) -> str | None:
    return result.matches[0].memory_id if result.matches else None


def _match_ids(result: Any) -> tuple[str, ...]:
    return tuple(match.memory_id for match in result.matches)


def _scope(match: Any) -> tuple[str | None, str | None]:
    metadata = dict(match.metadata)
    return (
        str(metadata.get("project_id"))
        if metadata.get("project_id") is not None
        else None,
        str(metadata.get("user_id"))
        if metadata.get("user_id") is not None
        else None,
    )




def _latest_metadata_records(paths: MemoryStoragePaths) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    path = paths.titan_metadata
    if not path.is_file():
        return records
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        memory_id = str(payload["memory_id"])
        records[memory_id] = payload
    return records


def _record_is_active(records: Mapping[str, Mapping[str, Any]], memory_id: str) -> bool:
    payload = records.get(memory_id)
    if payload is None:
        return False
    return bool(payload.get("active"))

def _record(
    checks: list[AuditCheck],
    *,
    seed: int,
    category: str,
    scenario: str,
    started: float,
    passed: bool,
    expected: str,
    observed: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    checks.append(
        AuditCheck(
            seed=seed,
            category=category,
            scenario=scenario,
            passed=bool(passed),
            duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            expected=expected,
            observed=observed,
            details=dict(details or {}),
        )
    )


def _add_distractors(
    gateway: MemoriXGateway,
    *,
    seed: int,
    count: int,
) -> None:
    rng = random.Random(seed * 131 + 42)
    values = ("UTC", "CET", "EST", "JST", "AEST", "IST")
    for index in range(count):
        project_id = f"DIST42-{seed}-{index:05d}"
        user_id = f"DISTUSER-{rng.randrange(1000):04d}"
        value = values[rng.randrange(len(values))]
        _validate_memory(
            gateway,
            content=(
                f"Tenant user {user_id} in project {project_id} has current "
                f"validated timezone token {value}_{index}; unrelated distractor."
            ),
            source_event_id=f"part42-distractor-{seed}-{index}",
            metadata={
                "benchmark": "part42",
                "family": "distractor",
                "project_id": project_id,
                "user_id": user_id,
                "decision_key": "timezone",
                "value": f"{value}_{index}",
            },
        )


def _precise_query(project_id: str, user_id: str) -> str:
    return (
        f"For tenant user {user_id} in project {project_id}, what is the "
        "current validated timezone token?"
    )


def _paraphrase_query(project_id: str, user_id: str) -> str:
    return (
        f"Which timezone setting belongs to {user_id} inside workspace "
        f"{project_id}?"
    )


def _tenant_matches(result: Any) -> list[Any]:
    return [
        match
        for match in result.matches
        if dict(match.metadata).get("family") in {
            "tenant_conflict",
            "tenant_project_conflict",
        }
    ]


def _run_seed(
    *,
    output_root: Path,
    seed: int,
    request: ResolvedTenantAuditRequest,
) -> tuple[list[AuditCheck], dict[str, Any]]:
    seed_root = output_root / "runtimes" / f"seed-{seed:08d}"
    paths = MemoryStoragePaths.from_runtime_root(seed_root)
    gateway = _make_gateway(paths, request, seed)
    checks: list[AuditCheck] = []

    distractor_started = time.perf_counter()
    _add_distractors(gateway, seed=seed, count=request.distractor_count)
    distractor_duration_ms = round(
        (time.perf_counter() - distractor_started) * 1000.0, 3
    )

    users = tuple(f"USER42-{seed}-{index:02d}" for index in range(request.user_count))
    projects = tuple(
        f"PROJECT42-{seed}-{index:02d}" for index in range(request.project_count)
    )
    primary_project = projects[0]
    memories: dict[tuple[str, str], Any] = {}

    for user_index, user_id in enumerate(users):
        value = f"ZONE_{seed}_{user_index:02d}"
        memories[(primary_project, user_id)] = _validate_memory(
            gateway,
            content=(
                f"Tenant user {user_id} in project {primary_project} has current "
                f"validated timezone token {value}."
            ),
            source_event_id=f"part42-user-primary-{seed}-{user_index}",
            metadata={
                "benchmark": "part42",
                "family": "tenant_conflict",
                "project_id": primary_project,
                "user_id": user_id,
                "decision_key": "timezone",
                "value": value,
            },
        )

    started = time.perf_counter()
    initial_records = _latest_metadata_records(paths)
    initial_storage_failures = [
        user_id
        for user_id in users
        if not _record_is_active(
            initial_records,
            memories[(primary_project, user_id)].memory_id,
        )
    ]
    _record(
        checks,
        seed=seed,
        category="storage",
        scenario="tenant_records_active_in_storage",
        started=started,
        passed=not initial_storage_failures,
        expected="all tenant memories active in metadata",
        observed=f"{len(initial_storage_failures)} inactive or missing",
        details={"failures": initial_storage_failures},
    )

    started = time.perf_counter()
    exact_failures: list[dict[str, Any]] = []
    for user_id in users:
        result = gateway.retrieve_memory(
            _precise_query(primary_project, user_id),
            top_k=request.top_k,
            project_id=primary_project,
            user_id=user_id,
        )
        expected_id = memories[(primary_project, user_id)].memory_id
        if _top_id(result) != expected_id:
            exact_failures.append(
                {
                    "user_id": user_id,
                    "expected": expected_id,
                    "observed": _top_id(result),
                }
            )
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="user_exact_top1",
        started=started,
        passed=not exact_failures,
        expected=f"{len(users)}/{len(users)} correct",
        observed=f"{len(users)-len(exact_failures)}/{len(users)} correct",
        details={"failures": exact_failures},
    )

    started = time.perf_counter()
    paraphrase_failures: list[dict[str, Any]] = []
    for user_id in users:
        result = gateway.retrieve_memory(
            _paraphrase_query(primary_project, user_id),
            top_k=request.top_k,
            project_id=primary_project,
            user_id=user_id,
        )
        expected_id = memories[(primary_project, user_id)].memory_id
        if _top_id(result) != expected_id:
            paraphrase_failures.append(
                {
                    "user_id": user_id,
                    "expected": expected_id,
                    "observed": _top_id(result),
                }
            )
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="user_paraphrase_top1",
        started=started,
        passed=not paraphrase_failures,
        expected=f"{len(users)}/{len(users)} correct",
        observed=f"{len(users)-len(paraphrase_failures)}/{len(users)} correct",
        details={"failures": paraphrase_failures},
    )

    started = time.perf_counter()
    user_leaks: list[dict[str, Any]] = []
    for user_id in users:
        result = gateway.retrieve_memory(
            _precise_query(primary_project, user_id),
            top_k=request.top_k,
            project_id=primary_project,
            user_id=user_id,
        )
        foreign = [
            {
                "memory_id": match.memory_id,
                "scope": _scope(match),
                "score": match.score,
            }
            for match in _tenant_matches(result)
            if _scope(match) != (primary_project, user_id)
        ]
        if foreign:
            user_leaks.append({"user_id": user_id, "foreign_matches": foreign})
    _record(
        checks,
        seed=seed,
        category="isolation",
        scenario="strict_cross_user_topk_isolation",
        started=started,
        passed=not user_leaks,
        expected="zero foreign user memories in top-k",
        observed=f"{len(user_leaks)} queries leaked foreign tenant memories",
        details={"leaks": user_leaks},
    )

    focal_user = users[0]
    for project_index, project_id in enumerate(projects[1:], start=1):
        value = f"PROJECT_ZONE_{seed}_{project_index:02d}"
        memories[(project_id, focal_user)] = _validate_memory(
            gateway,
            content=(
                f"Tenant user {focal_user} in project {project_id} has current "
                f"validated timezone token {value}."
            ),
            source_event_id=f"part42-project-{seed}-{project_index}",
            metadata={
                "benchmark": "part42",
                "family": "tenant_project_conflict",
                "project_id": project_id,
                "user_id": focal_user,
                "decision_key": "timezone",
                "value": value,
            },
        )

    started = time.perf_counter()
    project_failures: list[dict[str, Any]] = []
    for project_id in projects:
        result = gateway.retrieve_memory(
            _precise_query(project_id, focal_user),
            top_k=request.top_k,
            project_id=project_id,
            user_id=focal_user,
        )
        expected_id = memories[(project_id, focal_user)].memory_id
        if _top_id(result) != expected_id:
            project_failures.append(
                {
                    "project_id": project_id,
                    "expected": expected_id,
                    "observed": _top_id(result),
                }
            )
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="project_exact_top1",
        started=started,
        passed=not project_failures,
        expected=f"{len(projects)}/{len(projects)} correct",
        observed=f"{len(projects)-len(project_failures)}/{len(projects)} correct",
        details={"failures": project_failures},
    )

    started = time.perf_counter()
    project_leaks: list[dict[str, Any]] = []
    for project_id in projects:
        result = gateway.retrieve_memory(
            _precise_query(project_id, focal_user),
            top_k=request.top_k,
            project_id=project_id,
            user_id=focal_user,
        )
        foreign = [
            {
                "memory_id": match.memory_id,
                "scope": _scope(match),
                "score": match.score,
            }
            for match in _tenant_matches(result)
            if _scope(match) != (project_id, focal_user)
        ]
        if foreign:
            project_leaks.append(
                {"project_id": project_id, "foreign_matches": foreign}
            )
    _record(
        checks,
        seed=seed,
        category="isolation",
        scenario="strict_cross_project_topk_isolation",
        started=started,
        passed=not project_leaks,
        expected="zero foreign project memories in top-k",
        observed=f"{len(project_leaks)} queries leaked foreign project memories",
        details={"leaks": project_leaks},
    )

    target_user = users[0]
    previous = memories[(primary_project, target_user)]
    replacement_value = f"REPLACED_ZONE_{seed}"
    started = time.perf_counter()
    replacement = _validate_memory(
        gateway,
        content=(
            f"Tenant user {target_user} in project {primary_project} has current "
            f"validated timezone token {replacement_value}."
        ),
        source_event_id=f"part42-replacement-{seed}",
        target_memory_id=previous.memory_id,
        metadata={
            "benchmark": "part42",
            "family": "tenant_conflict",
            "project_id": primary_project,
            "user_id": target_user,
            "decision_key": "timezone",
            "value": replacement_value,
        },
    )
    memories[(primary_project, target_user)] = replacement
    replacement_result = gateway.retrieve_memory(
        _precise_query(primary_project, target_user),
        top_k=request.top_k,
        project_id=primary_project,
        user_id=target_user,
    )
    replacement_ids = _match_ids(replacement_result)
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="replacement_latest_top1_and_stale_absent",
        started=started,
        passed=(
            _top_id(replacement_result) == replacement.memory_id
            and previous.memory_id not in replacement_ids
        ),
        expected=replacement.memory_id,
        observed=str(_top_id(replacement_result)),
        details={
            "returned_ids": list(replacement_ids),
        },
    )

    started = time.perf_counter()
    replacement_records = _latest_metadata_records(paths)
    previous_record = replacement_records.get(previous.memory_id, {})
    replacement_record = replacement_records.get(replacement.memory_id, {})
    replacement_storage_passed = (
        replacement.version == 2
        and replacement.supersedes_memory_id == previous.memory_id
        and not _record_is_active(replacement_records, previous.memory_id)
        and _record_is_active(replacement_records, replacement.memory_id)
        and int(replacement_record.get("metadata", {}).get("version", 0)) == 2
        and replacement_record.get("metadata", {}).get("supersedes_memory_id")
        == previous.memory_id
    )
    _record(
        checks,
        seed=seed,
        category="storage",
        scenario="replacement_storage_lineage_is_correct",
        started=started,
        passed=replacement_storage_passed,
        expected="old inactive; new active version 2; correct supersedes link",
        observed=(
            f"old_active={_record_is_active(replacement_records, previous.memory_id)}; "
            f"new_active={_record_is_active(replacement_records, replacement.memory_id)}; "
            f"version={replacement_record.get('metadata', {}).get('version')}"
        ),
        details={
            "previous_record": previous_record,
            "replacement_record": replacement_record,
        },
    )

    started = time.perf_counter()
    unaffected_storage_failures = [
        user_id
        for user_id in users[1:]
        if not _record_is_active(
            replacement_records,
            memories[(primary_project, user_id)].memory_id,
        )
    ]
    _record(
        checks,
        seed=seed,
        category="storage",
        scenario="replacement_storage_is_tenant_local",
        started=started,
        passed=not unaffected_storage_failures,
        expected="all non-target tenant records remain active",
        observed=f"{len(unaffected_storage_failures)} inactive records",
        details={"affected_users": unaffected_storage_failures},
    )

    started = time.perf_counter()
    restarted = _make_gateway(paths, request, seed)
    restart_result = restarted.retrieve_memory(
        _precise_query(primary_project, target_user),
        top_k=request.top_k,
        project_id=primary_project,
        user_id=target_user,
    )
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="replacement_retrieval_after_restart",
        started=started,
        passed=_top_id(restart_result) == replacement.memory_id,
        expected=replacement.memory_id,
        observed=str(_top_id(restart_result)),
        details={"returned_ids": list(_match_ids(restart_result))},
    )
    started = time.perf_counter()
    restart_records = _latest_metadata_records(paths)
    _record(
        checks,
        seed=seed,
        category="storage",
        scenario="replacement_storage_persists_after_restart",
        started=started,
        passed=(
            _record_is_active(restart_records, replacement.memory_id)
            and not _record_is_active(restart_records, previous.memory_id)
        ),
        expected="replacement active and stale version inactive after restart",
        observed=(
            f"replacement_active={_record_is_active(restart_records, replacement.memory_id)}; "
            f"stale_active={_record_is_active(restart_records, previous.memory_id)}"
        ),
    )
    gateway = restarted

    forgotten_user = users[1]
    forgotten_memory = memories[(primary_project, forgotten_user)]
    started = time.perf_counter()
    forget = gateway.forget_memory(
        forgotten_memory.memory_id,
        validated_by="part42_benchmark_reviewer",
        reason="Tenant-scoped forget audit.",
    )
    forgotten_restart = _make_gateway(paths, request, seed)
    forgotten_result = forgotten_restart.retrieve_memory(
        _precise_query(primary_project, forgotten_user),
        top_k=request.top_k,
        project_id=primary_project,
        user_id=forgotten_user,
    )
    _record(
        checks,
        seed=seed,
        category="retrieval",
        scenario="forgotten_memory_absent_from_retrieval",
        started=started,
        passed=(
            forget.action is ForgetAction.DEACTIVATED
            and forgotten_memory.memory_id not in _match_ids(forgotten_result)
        ),
        expected="forgotten memory absent after restart",
        observed=f"returned={forgotten_memory.memory_id in _match_ids(forgotten_result)}",
        details={
            "forget_action": forget.action.value,
            "returned_ids": list(_match_ids(forgotten_result)),
        },
    )
    started = time.perf_counter()
    forget_records = _latest_metadata_records(paths)
    other_storage_failures = [
        user_id
        for user_id in users
        if user_id != forgotten_user
        and not _record_is_active(
            forget_records,
            memories[(primary_project, user_id)].memory_id,
        )
    ]
    _record(
        checks,
        seed=seed,
        category="storage",
        scenario="forget_storage_is_tenant_local_after_restart",
        started=started,
        passed=(
            not _record_is_active(forget_records, forgotten_memory.memory_id)
            and not other_storage_failures
        ),
        expected="forgotten record inactive; all other tenant records active",
        observed=(
            f"forgotten_active={_record_is_active(forget_records, forgotten_memory.memory_id)}; "
            f"other_inactive={len(other_storage_failures)}"
        ),
        details={"other_inactive_users": other_storage_failures},
    )
    gateway = forgotten_restart

    started = time.perf_counter()
    signature = inspect.signature(MemoriXGateway.retrieve_memory)
    parameters = set(signature.parameters)
    scoped_contract = {"project_id", "user_id"}.issubset(parameters)
    _record(
        checks,
        seed=seed,
        category="contract",
        scenario="gateway_has_explicit_tenant_filters",
        started=started,
        passed=scoped_contract,
        expected="retrieve_memory accepts project_id and user_id filters",
        observed="parameters=" + ",".join(sorted(parameters)),
        details={"parameters": sorted(parameters)},
    )

    started = time.perf_counter()
    broad = gateway.retrieve_memory(
        "What is the current validated timezone token?",
        top_k=request.top_k,
    )
    broad_scopes = sorted(
        {
            scope
            for scope in (_scope(match) for match in _tenant_matches(broad))
            if scope != (None, None)
        }
    )
    _record(
        checks,
        seed=seed,
        category="diagnostic",
        scenario="broad_query_scope_ambiguity_observed",
        started=started,
        passed=True,
        expected="diagnostic only",
        observed=f"{len(broad_scopes)} tenant scopes in top-k",
        details={
            "scopes": [list(scope) for scope in broad_scopes],
            "matches": [match.to_dict() for match in broad.matches],
        },
    )

    status = gateway.memory_status()
    summary = {
        "seed": seed,
        "user_count": request.user_count,
        "project_count": request.project_count,
        "distractor_count": request.distractor_count,
        "check_count": len(checks),
        "passed_check_count": sum(check.passed for check in checks),
        "distractor_ingestion_duration_ms": distractor_duration_ms,
        "status": status,
    }
    _write_json(
        output_root / "seed_summaries" / f"seed-{seed:08d}.json",
        summary,
    )
    return checks, summary


def _mean(values: Sequence[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _aggregate(checks: Sequence[AuditCheck]) -> dict[str, Any]:
    categories: dict[str, dict[str, Any]] = {}
    scenarios: dict[str, dict[str, Any]] = {}
    for check in checks:
        category = categories.setdefault(
            check.category,
            {"count": 0, "passed": 0, "durations": []},
        )
        category["count"] += 1
        category["passed"] += int(check.passed)
        category["durations"].append(check.duration_ms)
        scenario = scenarios.setdefault(
            check.scenario,
            {"count": 0, "passed": 0, "durations": []},
        )
        scenario["count"] += 1
        scenario["passed"] += int(check.passed)
        scenario["durations"].append(check.duration_ms)

    def finish(payload: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "count": value["count"],
                "passed": value["passed"],
                "failed": value["count"] - value["passed"],
                "success_rate": round(value["passed"] / value["count"], 6),
                "mean_duration_ms": _mean(value["durations"]),
            }
            for key, value in sorted(payload.items())
        }

    finished_categories = finish(categories)
    finished_scenarios = finish(scenarios)
    storage_checks = [check for check in checks if check.category == "storage"]
    retrieval_checks = [check for check in checks if check.category == "retrieval"]
    isolation_checks = [check for check in checks if check.category in {"isolation", "contract"}]
    return {
        "check_count": len(checks),
        "passed_check_count": sum(check.passed for check in checks),
        "failed_check_count": sum(not check.passed for check in checks),
        "categories": finished_categories,
        "scenarios": finished_scenarios,
        "storage_lifecycle_gate_passed": all(check.passed for check in storage_checks),
        "retrieval_namespace_gate_passed": all(check.passed for check in retrieval_checks),
        "tenant_isolation_gate_passed": all(check.passed for check in isolation_checks),
        "storage_check_count": len(storage_checks),
        "retrieval_check_count": len(retrieval_checks),
        "isolation_check_count": len(isolation_checks),
        "retrieval_warning_count": sum(not check.passed for check in retrieval_checks),
        "isolation_warning_count": sum(not check.passed for check in isolation_checks),
    }


def _write_checks(output_root: Path, checks: Sequence[AuditCheck]) -> tuple[Path, Path]:
    jsonl_path = output_root / "tenant_contradiction_checks.jsonl"
    with jsonl_path.open("wb") as handle:
        for check in checks:
            handle.write(_canonical_bytes(check.to_dict()))
    csv_path = output_root / "tenant_contradiction_checks.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "seed",
                "category",
                "scenario",
                "passed",
                "duration_ms",
                "expected",
                "observed",
                "details_json",
            ),
        )
        writer.writeheader()
        for check in checks:
            payload = check.to_dict()
            writer.writerow(
                {
                    "seed": payload["seed"],
                    "category": payload["category"],
                    "scenario": payload["scenario"],
                    "passed": payload["passed"],
                    "duration_ms": payload["duration_ms"],
                    "expected": payload["expected"],
                    "observed": payload["observed"],
                    "details_json": json.dumps(payload["details"], sort_keys=True),
                }
            )
    return jsonl_path, csv_path


def run_tenant_audit(
    *,
    repository_root: Path,
    output_root: Path,
    archive_path: Path,
    request: TenantAuditRequest,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    output_root = output_root.resolve()
    archive_path = archive_path.resolve()
    resolved = request.resolved()
    if output_root == repository_root or repository_root in output_root.parents:
        raise ValueError("Output must be outside the repository.")
    if archive_path == repository_root or repository_root in archive_path.parents:
        raise ValueError("Archive must be outside the repository.")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output: {output_root}")
    if archive_path.exists():
        raise FileExistsError(f"Archive already exists: {archive_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    before = protected_snapshot(repository_root)
    _write_json(output_root / "protected_before.json", before)
    _write_json(output_root / "campaign_request.json", asdict(resolved))

    started = time.perf_counter()
    checks: list[AuditCheck] = []
    summaries: list[dict[str, Any]] = []
    for seed in resolved.seeds:
        seed_checks, summary = _run_seed(
            output_root=output_root,
            seed=seed,
            request=resolved,
        )
        checks.extend(seed_checks)
        summaries.append(summary)

    after = protected_snapshot(repository_root)
    differences = compare_snapshots(before, after)
    protected_unchanged = not any(differences.values())
    _write_json(output_root / "protected_after.json", after)
    _write_json(output_root / "protected_diff.json", differences)
    jsonl_path, csv_path = _write_checks(output_root, checks)
    aggregates = _aggregate(checks)

    report = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "campaign_type": "real_tenant_contradiction_audit",
        "completed": True,
        "request": asdict(resolved),
        "seed_count": len(resolved.seeds),
        "aggregates": aggregates,
        "seed_summaries": summaries,
        "protected_core_unchanged": protected_unchanged,
        "protected_core_differences": differences,
        "total_duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "artifacts": {
            "checks_jsonl": jsonl_path.name,
            "checks_csv": csv_path.name,
            "runtimes_directory": "runtimes",
            "seed_summaries_directory": "seed_summaries",
            "protected_before": "protected_before.json",
            "protected_after": "protected_after.json",
            "protected_diff": "protected_diff.json",
        },
    }
    report_path = output_root / "tenant_contradiction_audit_report.json"
    _write_json(report_path, report)

    if not protected_unchanged:
        raise RuntimeError("Protected source files changed; results preserved for audit.")

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    created = Path(
        shutil.make_archive(
            str(archive_path.with_suffix("")),
            "zip",
            root_dir=output_root.parent,
            base_dir=output_root.name,
        )
    )
    if created != archive_path:
        if archive_path.exists():
            archive_path.unlink()
        created.replace(archive_path)
    return report


def validate_tenant_audit_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version.")
    if report.get("campaign_version") != CAMPAIGN_VERSION:
        raise ValueError("Invalid campaign_version.")
    if report.get("campaign_type") != "real_tenant_contradiction_audit":
        raise ValueError("Invalid campaign_type.")
    if report.get("completed") is not True:
        raise ValueError("Campaign is incomplete.")
    if report.get("protected_core_unchanged") is not True:
        raise ValueError("Protected core changed.")
    if int(report.get("seed_count", 0)) < 1:
        raise ValueError("No seeds were recorded.")
    if int(report.get("aggregates", {}).get("check_count", 0)) < 1:
        raise ValueError("No checks were recorded.")
    return report
