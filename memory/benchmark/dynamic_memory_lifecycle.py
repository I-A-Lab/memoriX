"""Real dynamic-memory lifecycle benchmark for memoriX.

This benchmark exercises the public Python gateway and the real Titan hot site.
It does not call an LLM and never mutates source files. Runtime data and results
must be stored outside the repository.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import json
import random
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch

from memory.data import CandidateStatus, ForgetAction, MemoryStoragePaths
from memory.gateway import MemoriXGateway

SCHEMA_VERSION = 1
CAMPAIGN_VERSION = "41.0.0"

PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "quick": {
        "seeds": (101, 202),
        "distractor_count": 25,
        "update_count": 2,
        "titan_dim": 32,
        "top_k": 10,
    },
    "standard": {
        "seeds": (101, 202, 303),
        "distractor_count": 250,
        "update_count": 3,
        "titan_dim": 48,
        "top_k": 10,
    },
    "stress": {
        "seeds": (101, 202, 303),
        "distractor_count": 1000,
        "update_count": 5,
        "titan_dim": 64,
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
class DynamicCampaignRequest:
    profile: str = "quick"
    seeds: tuple[int, ...] | None = None
    distractor_count: int | None = None
    update_count: int | None = None
    titan_dim: int | None = None
    top_k: int | None = None

    def resolved(self) -> "ResolvedDynamicCampaignRequest":
        if self.profile not in PROFILE_SPECS:
            raise ValueError(
                "profile must be one of: " + ", ".join(PROFILE_SPECS)
            )
        spec = PROFILE_SPECS[self.profile]
        seeds = tuple(self.seeds or spec["seeds"])
        if not seeds:
            raise ValueError("At least one seed is required.")
        if len(set(seeds)) != len(seeds):
            raise ValueError("Duplicate seeds are not allowed.")
        distractor_count = int(
            spec["distractor_count"]
            if self.distractor_count is None
            else self.distractor_count
        )
        update_count = int(
            spec["update_count"]
            if self.update_count is None
            else self.update_count
        )
        titan_dim = int(
            spec["titan_dim"] if self.titan_dim is None else self.titan_dim
        )
        top_k = int(spec["top_k"] if self.top_k is None else self.top_k)
        if distractor_count < 0:
            raise ValueError("distractor_count must be non-negative.")
        if update_count < 1:
            raise ValueError("update_count must be positive.")
        if titan_dim < 16:
            raise ValueError("titan_dim must be at least 16.")
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        return ResolvedDynamicCampaignRequest(
            profile=self.profile,
            seeds=tuple(int(seed) for seed in seeds),
            distractor_count=distractor_count,
            update_count=update_count,
            titan_dim=titan_dim,
            top_k=top_k,
        )


@dataclass(frozen=True, slots=True)
class ResolvedDynamicCampaignRequest:
    profile: str
    seeds: tuple[int, ...]
    distractor_count: int
    update_count: int
    titan_dim: int
    top_k: int


@dataclass(frozen=True, slots=True)
class CheckResult:
    seed: int
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


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(payload))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
            key = path.relative_to(repository_root).as_posix()
            snapshot[key] = _hash_file(path)
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
    request: ResolvedDynamicCampaignRequest,
    seed: int,
) -> MemoriXGateway:
    gc.collect()
    torch.manual_seed(seed)
    return MemoriXGateway(
        storage_paths=paths,
        titan_d_model=request.titan_dim,
        titan_hidden_dim=request.titan_dim,
        titan_max_items=max(500, request.distractor_count + 100),
        titan_device="cpu",
        titan_top_k=request.top_k,
        titan_min_score=0.0,
    )


def _validate_memory(
    gateway: MemoriXGateway,
    *,
    content: str,
    source_event_id: str,
    reason: str,
    metadata: Mapping[str, Any],
    target_memory_id: str | None = None,
):
    candidate = gateway.propose_memory_candidate(
        content=content,
        reason=reason,
        source_event_ids=(source_event_id,),
        importance=0.95,
        confidence=1.0,
        surprise=0.65,
        target_memory_id=target_memory_id,
        metadata=dict(metadata),
    )
    return gateway.validate_memory_candidate(
        candidate.candidate_id,
        validated_by="benchmark_reviewer",
        validation_reason="Approved by the dynamic lifecycle benchmark.",
    )


def _match_ids(result: Any) -> tuple[str, ...]:
    return tuple(match.memory_id for match in result.matches)


def _top_id(result: Any) -> str | None:
    return result.matches[0].memory_id if result.matches else None


def _top_content(result: Any) -> str:
    return result.matches[0].content if result.matches else ""


def _record_check(
    checks: list[CheckResult],
    *,
    seed: int,
    scenario: str,
    started: float,
    passed: bool,
    expected: str,
    observed: str,
    details: Mapping[str, Any] | None = None,
) -> None:
    checks.append(
        CheckResult(
            seed=seed,
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
) -> tuple[str, ...]:
    rng = random.Random(seed * 97 + 41)
    ids: list[str] = []
    separators = ("comma", "semicolon", "pipe", "tab")
    for index in range(count):
        project = f"DIST41-{seed}-{index:05d}"
        separator = separators[rng.randrange(len(separators))]
        memory = _validate_memory(
            gateway,
            content=(
                f"Workspace {project} validated export separator is "
                f"{separator}; unrelated benchmark distractor {index}."
            ),
            source_event_id=f"event-distractor-{seed}-{index}",
            reason="Dynamic benchmark stress distractor.",
            metadata={
                "benchmark": "part41",
                "family": "distractor",
                "project_id": project,
                "seed": seed,
            },
        )
        ids.append(memory.memory_id)
    return tuple(ids)


def _run_seed(
    *,
    output_root: Path,
    seed: int,
    request: ResolvedDynamicCampaignRequest,
) -> tuple[list[CheckResult], dict[str, Any]]:
    seed_root = output_root / "runtimes" / f"seed-{seed:08d}"
    paths = MemoryStoragePaths.from_runtime_root(seed_root)
    gateway = _make_gateway(paths, request, seed)
    checks: list[CheckResult] = []

    distractor_started = time.perf_counter()
    distractor_ids = _add_distractors(
        gateway,
        seed=seed,
        count=request.distractor_count,
    )
    distractor_duration_ms = round(
        (time.perf_counter() - distractor_started) * 1000.0, 3
    )

    project_alpha = f"DYN41-{seed}-ALPHA"
    alpha_values = [
        f"SEMICOLON_{seed}",
        f"PIPE_{seed}",
        f"TAB_{seed}",
        f"COMMA_{seed}",
        f"COLON_{seed}",
        f"SPACE_{seed}",
    ]

    started = time.perf_counter()
    alpha = _validate_memory(
        gateway,
        content=(
            f"Workspace {project_alpha} current validated export delimiter "
            f"is token {alpha_values[0]}."
        ),
        source_event_id=f"event-alpha-initial-{seed}",
        reason="Initial project decision.",
        metadata={
            "benchmark": "part41",
            "family": "dynamic_update",
            "project_id": project_alpha,
            "decision_key": "export_delimiter",
            "value": alpha_values[0],
        },
    )
    initial_exact = gateway.retrieve_memory(
        f"Workspace {project_alpha} current validated export delimiter",
        top_k=request.top_k,
    )
    _record_check(
        checks,
        seed=seed,
        scenario="create_retrieve_exact",
        started=started,
        passed=_top_id(initial_exact) == alpha.memory_id,
        expected=alpha.memory_id,
        observed=str(_top_id(initial_exact)),
        details={"top_content": _top_content(initial_exact)},
    )

    started = time.perf_counter()
    initial_paraphrase = gateway.retrieve_memory(
        f"For workspace {project_alpha}, which token separates exported columns?",
        top_k=request.top_k,
    )
    _record_check(
        checks,
        seed=seed,
        scenario="create_retrieve_paraphrase",
        started=started,
        passed=_top_id(initial_paraphrase) == alpha.memory_id,
        expected=alpha.memory_id,
        observed=str(_top_id(initial_paraphrase)),
        details={"top_content": _top_content(initial_paraphrase)},
    )

    lineage = [alpha]
    for update_index in range(1, request.update_count + 1):
        previous = lineage[-1]
        value = alpha_values[update_index]
        started = time.perf_counter()
        updated = _validate_memory(
            gateway,
            content=(
                f"Workspace {project_alpha} current validated export delimiter "
                f"is token {value}."
            ),
            source_event_id=f"event-alpha-update-{seed}-{update_index}",
            reason="Validated correction replacing the previous decision.",
            metadata={
                "benchmark": "part41",
                "family": "dynamic_update",
                "project_id": project_alpha,
                "decision_key": "export_delimiter",
                "value": value,
                "update_index": update_index,
            },
            target_memory_id=previous.memory_id,
        )
        lineage.append(updated)
        update_result = gateway.retrieve_memory(
            f"Workspace {project_alpha} current validated export delimiter",
            top_k=request.top_k,
        )
        ids = _match_ids(update_result)
        passed = (
            updated.version == update_index + 1
            and updated.supersedes_memory_id == previous.memory_id
            and _top_id(update_result) == updated.memory_id
            and previous.memory_id not in ids
        )
        _record_check(
            checks,
            seed=seed,
            scenario=f"update_replace_{update_index}",
            started=started,
            passed=passed,
            expected=updated.memory_id,
            observed=str(_top_id(update_result)),
            details={
                "version": updated.version,
                "supersedes_memory_id": updated.supersedes_memory_id,
                "returned_ids": list(ids),
                "top_content": _top_content(update_result),
            },
        )

    final_alpha = lineage[-1]
    started = time.perf_counter()
    restarted = _make_gateway(paths, request, seed)
    restart_result = restarted.retrieve_memory(
        f"Workspace {project_alpha} current validated export delimiter",
        top_k=request.top_k,
    )
    _record_check(
        checks,
        seed=seed,
        scenario="restart_persistence_after_updates",
        started=started,
        passed=_top_id(restart_result) == final_alpha.memory_id,
        expected=final_alpha.memory_id,
        observed=str(_top_id(restart_result)),
        details={"top_content": _top_content(restart_result)},
    )
    gateway = restarted

    project_beta = f"DYN41-{seed}-BETA"
    project_gamma = f"DYN41-{seed}-GAMMA"
    beta_value = f"BETA_DASH_{seed}"
    gamma_value = f"GAMMA_UNDERSCORE_{seed}"
    beta = _validate_memory(
        gateway,
        content=(
            f"Workspace {project_beta} current validated username separator "
            f"is token {beta_value}."
        ),
        source_event_id=f"event-beta-{seed}",
        reason="Project-specific username policy.",
        metadata={
            "benchmark": "part41",
            "family": "project_isolation",
            "project_id": project_beta,
            "decision_key": "username_separator",
            "value": beta_value,
        },
    )
    gamma = _validate_memory(
        gateway,
        content=(
            f"Workspace {project_gamma} current validated username separator "
            f"is token {gamma_value}."
        ),
        source_event_id=f"event-gamma-{seed}",
        reason="Project-specific username policy.",
        metadata={
            "benchmark": "part41",
            "family": "project_isolation",
            "project_id": project_gamma,
            "decision_key": "username_separator",
            "value": gamma_value,
        },
    )

    for label, project, memory in (
        ("beta", project_beta, beta),
        ("gamma", project_gamma, gamma),
    ):
        started = time.perf_counter()
        result = gateway.retrieve_memory(
            f"Workspace {project} current validated username separator",
            top_k=request.top_k,
        )
        _record_check(
            checks,
            seed=seed,
            scenario=f"project_isolation_{label}",
            started=started,
            passed=_top_id(result) == memory.memory_id,
            expected=memory.memory_id,
            observed=str(_top_id(result)),
            details={"top_content": _top_content(result)},
        )

    started = time.perf_counter()
    forget = gateway.forget_memory(
        beta.memory_id,
        validated_by="benchmark_reviewer",
        reason="Dynamic benchmark explicit forget test.",
    )
    forgotten_restart = _make_gateway(paths, request, seed)
    forgotten_result = forgotten_restart.retrieve_memory(
        f"Workspace {project_beta} current validated username separator",
        top_k=request.top_k,
    )
    forgotten_ids = _match_ids(forgotten_result)
    status_after_forget = forgotten_restart.memory_status()
    _record_check(
        checks,
        seed=seed,
        scenario="forget_persists_after_restart",
        started=started,
        passed=(
            forget.action is ForgetAction.DEACTIVATED
            and beta.memory_id not in forgotten_ids
        ),
        expected="deactivated_and_absent",
        observed=(
            f"action={forget.action.value}; returned={beta.memory_id in forgotten_ids}"
        ),
        details={
            "returned_ids": list(forgotten_ids),
            "hot_memories_total": status_after_forget["hot_memories_total"],
            "hot_memories_active": status_after_forget["hot_memories_active"],
        },
    )
    gateway = forgotten_restart

    consolidation_project = f"DYN41-{seed}-CONSOLIDATION"
    consolidation_token = f"SIGNED_{seed}"
    event_id = f"event-consolidation-{seed}"
    started = time.perf_counter()
    gateway.record_memory_event(
        event_id=event_id,
        content=(
            f"Workspace {consolidation_project} validated release artifact "
            f"suffix is token {consolidation_token}."
        ),
        event_type="architecture_rule",
        source="part41_dynamic_benchmark",
        project_id=consolidation_project,
        session_id=f"session-{seed}-consolidation",
        importance=0.98,
        confidence=1.0,
        surprise=0.75,
        metadata={
            "benchmark": "part41",
            "family": "consolidation",
            "decision_key": "release_suffix",
            "value": consolidation_token,
        },
    )
    first_consolidation = gateway.run_consolidation(mode="part41_first")
    pending = gateway.list_memory_candidates(status=CandidateStatus.PENDING)
    source_candidates = [
        candidate for candidate in pending if event_id in candidate.source_event_ids
    ]
    _record_check(
        checks,
        seed=seed,
        scenario="consolidation_creates_candidate",
        started=started,
        passed=(
            first_consolidation.candidates_created >= 1
            and len(source_candidates) == 1
        ),
        expected="one_pending_candidate",
        observed=f"created={first_consolidation.candidates_created}; matched={len(source_candidates)}",
        details=first_consolidation.to_dict(),
    )

    started = time.perf_counter()
    consolidated_memory = gateway.validate_memory_candidate(
        source_candidates[0].candidate_id,
        validated_by="benchmark_reviewer",
        validation_reason="Approved consolidation candidate.",
    )
    consolidation_restart = _make_gateway(paths, request, seed)
    consolidation_result = consolidation_restart.retrieve_memory(
        f"Workspace {consolidation_project} validated release artifact suffix",
        top_k=request.top_k,
    )
    _record_check(
        checks,
        seed=seed,
        scenario="consolidation_validate_retrieve_restart",
        started=started,
        passed=_top_id(consolidation_result) == consolidated_memory.memory_id,
        expected=consolidated_memory.memory_id,
        observed=str(_top_id(consolidation_result)),
        details={"top_content": _top_content(consolidation_result)},
    )
    gateway = consolidation_restart

    started = time.perf_counter()
    second_consolidation = gateway.run_consolidation(mode="part41_duplicate")
    _record_check(
        checks,
        seed=seed,
        scenario="consolidation_duplicate_prevention",
        started=started,
        passed=(
            second_consolidation.candidates_created == 0
            and second_consolidation.duplicate_groups_skipped >= 1
        ),
        expected="created=0_and_duplicate_skipped",
        observed=(
            f"created={second_consolidation.candidates_created}; "
            f"skipped={second_consolidation.duplicate_groups_skipped}"
        ),
        details=second_consolidation.to_dict(),
    )

    started = time.perf_counter()
    cold_result = gateway.search_cold_site_history(
        f"Workspace {consolidation_project} release artifact suffix",
        limit=request.top_k,
    )
    cold_contents = tuple(match.content for match in cold_result.matches)
    _record_check(
        checks,
        seed=seed,
        scenario="cold_history_persists",
        started=started,
        passed=any(consolidation_token in content for content in cold_contents),
        expected=consolidation_token,
        observed=" | ".join(cold_contents[:3]),
        details={"match_count": len(cold_contents)},
    )

    seed_summary = {
        "seed": seed,
        "runtime_root": str(seed_root),
        "distractor_count": len(distractor_ids),
        "distractor_ingestion_duration_ms": distractor_duration_ms,
        "update_count": request.update_count,
        "check_count": len(checks),
        "passed_check_count": sum(check.passed for check in checks),
        "status": gateway.memory_status(),
    }
    return checks, seed_summary


def _aggregate_checks(checks: Sequence[CheckResult]) -> dict[str, Any]:
    by_scenario: dict[str, list[CheckResult]] = {}
    for check in checks:
        by_scenario.setdefault(check.scenario, []).append(check)
    scenario_metrics = {
        scenario: {
            "count": len(rows),
            "passed": sum(row.passed for row in rows),
            "success_rate": round(
                sum(row.passed for row in rows) / len(rows), 6
            ),
            "mean_duration_ms": round(
                statistics.fmean(row.duration_ms for row in rows), 3
            ),
        }
        for scenario, rows in sorted(by_scenario.items())
    }
    total = len(checks)
    passed = sum(check.passed for check in checks)
    return {
        "check_count": total,
        "passed_check_count": passed,
        "failed_check_count": total - passed,
        "success_rate": round(passed / total, 6) if total else 0.0,
        "scenarios": scenario_metrics,
    }


def _write_checks(
    output_root: Path, checks: Sequence[CheckResult]
) -> tuple[Path, Path]:
    jsonl_path = output_root / "dynamic_memory_checks.jsonl"
    with jsonl_path.open("wb") as handle:
        for check in checks:
            handle.write(_canonical_json_bytes(check.to_dict()))

    csv_path = output_root / "dynamic_memory_checks.csv"
    fieldnames = (
        "seed",
        "scenario",
        "passed",
        "duration_ms",
        "expected",
        "observed",
        "details_json",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for check in checks:
            writer.writerow(
                {
                    "seed": check.seed,
                    "scenario": check.scenario,
                    "passed": check.passed,
                    "duration_ms": check.duration_ms,
                    "expected": check.expected,
                    "observed": check.observed,
                    "details_json": json.dumps(
                        dict(check.details), sort_keys=True
                    ),
                }
            )
    return jsonl_path, csv_path


def run_dynamic_campaign(
    *,
    repository_root: Path,
    output_root: Path,
    archive_path: Path,
    request: DynamicCampaignRequest,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    output_root = output_root.resolve()
    archive_path = archive_path.resolve()
    resolved = request.resolved()

    if repository_root == output_root or repository_root in output_root.parents:
        raise ValueError("Output must be outside the source repository.")
    if repository_root == archive_path or repository_root in archive_path.parents:
        raise ValueError("Archive must be outside the source repository.")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty output: {output_root}")
    if archive_path.exists():
        raise FileExistsError(f"Archive already exists: {archive_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    before = protected_snapshot(repository_root)
    _write_json(output_root / "protected_before.json", before)
    _write_json(output_root / "campaign_request.json", asdict(resolved))

    started = time.perf_counter()
    all_checks: list[CheckResult] = []
    seed_summaries: list[dict[str, Any]] = []
    for seed in resolved.seeds:
        checks, summary = _run_seed(
            output_root=output_root,
            seed=seed,
            request=resolved,
        )
        all_checks.extend(checks)
        seed_summaries.append(summary)
        _write_json(
            output_root / "seed_summaries" / f"seed-{seed:08d}.json",
            summary,
        )

    after = protected_snapshot(repository_root)
    differences = compare_snapshots(before, after)
    protected_unchanged = not any(differences.values())
    _write_json(output_root / "protected_after.json", after)
    _write_json(output_root / "protected_diff.json", differences)

    checks_jsonl, checks_csv = _write_checks(output_root, all_checks)
    aggregate = _aggregate_checks(all_checks)
    report = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "campaign_type": "real_dynamic_memory_lifecycle",
        "completed": (
            aggregate["failed_check_count"] == 0 and protected_unchanged
        ),
        "request": asdict(resolved),
        "seed_count": len(resolved.seeds),
        "seed_summaries": seed_summaries,
        "aggregates": aggregate,
        "protected_core_unchanged": protected_unchanged,
        "protected_core_differences": differences,
        "total_duration_ms": round(
            (time.perf_counter() - started) * 1000.0, 3
        ),
        "artifacts": {
            "checks_jsonl": checks_jsonl.name,
            "checks_csv": checks_csv.name,
            "runtimes_directory": "runtimes",
            "seed_summaries_directory": "seed_summaries",
            "protected_before": "protected_before.json",
            "protected_after": "protected_after.json",
            "protected_diff": "protected_diff.json",
        },
    }
    report_path = output_root / "dynamic_memory_campaign_report.json"
    _write_json(report_path, report)

    if not protected_unchanged:
        raise RuntimeError(
            "Protected source files changed; results were preserved for audit."
        )
    if aggregate["failed_check_count"]:
        raise RuntimeError(
            f"{aggregate['failed_check_count']} dynamic-memory check(s) failed. "
            "Results were preserved; do not run a larger profile yet."
        )

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


def validate_dynamic_report(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version.")
    if report.get("campaign_version") != CAMPAIGN_VERSION:
        raise ValueError("Invalid campaign_version.")
    if report.get("campaign_type") != "real_dynamic_memory_lifecycle":
        raise ValueError("Invalid campaign_type.")
    if report.get("completed") is not True:
        raise ValueError("Campaign is not complete.")
    if report.get("protected_core_unchanged") is not True:
        raise ValueError("Protected core changed.")
    aggregate = report.get("aggregates", {})
    if int(aggregate.get("failed_check_count", -1)) != 0:
        raise ValueError("Dynamic-memory failures remain.")
    if int(aggregate.get("check_count", 0)) < 1:
        raise ValueError("No checks were recorded.")
    return report
