"""Adapter bridging the new orchestrator to the existing real OpenCode runners.

This module wraps opencode_real_campaign.py functions and adapts them
to produce RunResult objects compatible with the new orchestrator pipeline.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Guard: these imports must NEVER reach runtime outside the benchmark.
# ---------------------------------------------------------------------------
_BENCH_ROOT = Path(__file__).resolve().parents[1]
assert _BENCH_ROOT.name == "benchmarks", (
    "RealRunnerAdapter must live inside benchmarks/"
)

# ---------------------------------------------------------------------------
# Lazy import of the real runner module (avoids polluting top-level namespace).
# ---------------------------------------------------------------------------
_REAL_RUNNER_PATH = _BENCH_ROOT.parent / "memory" / "benchmark" / "opencode_real_campaign.py"


def _load_real_runner():
    """Dynamically load the real runner module."""
    if not _REAL_RUNNER_PATH.is_file():
        raise FileNotFoundError(
            f"Real runner not found at {_REAL_RUNNER_PATH}. "
            "Cannot run real OpenCode benchmarks."
        )
    spec = importlib.util.spec_from_file_location(
        "opencode_real_campaign", str(_REAL_RUNNER_PATH)
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load spec for {_REAL_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Mapping from new orchestrator family IDs to real runner TASK_KINDS.
# ---------------------------------------------------------------------------
FAMILY_TO_KIND: dict[str, str] = {
    "f01_exact_key_recall": "csv_delimiter",
    "f02_semantic_retrieval": "username_separator",
    "f03_distractor_robustness": "retry_schedule",
    "f04_multi_hop_reasoning": "date_format",
    "f05_temporal_decay": "cache_key",
    "f06_contextual_disambiguation": "page_size",
    "f07_adversarial_injection": "boolean_tokens",
    "f08_cross_session_leak": "filename_policy",
    "f09_privacy_isolation": "csv_delimiter",
    "f10_consolidation_quality": "username_separator",
    "f11_forgetting_curve": "retry_schedule",
    "f12_capacity_management": "date_format",
    "f13_search_precision": "cache_key",
    "f14_search_recall": "page_size",
    "f15_ranking_relevance": "boolean_tokens",
    "f16_query_expansion": "filename_policy",
    "f17_partial_match": "csv_delimiter",
    "f18_noise_tolerance": "username_separator",
    "f19_schema_evolution": "retry_schedule",
    "f20_version_awareness": "date_format",
    "f21_concurrent_access": "cache_key",
    "f22_migration_safety": "page_size",
    "f23_api_conformance": "boolean_tokens",
    "f24_sdk_compatibility": "filename_policy",
    "f25_performance_baseline": "csv_delimiter",
    "f26_latency_budget": "username_separator",
    "f27_memory_footprint": "retry_schedule",
    "f28_streaming_integrity": "date_format",
    "f29_end_to_end_smoke": "cache_key",
    "f30_reproducibility": "page_size",
    "f31_determinism_check": "boolean_tokens",
    "f32_golden_output": "filename_policy",
}

# Reverse mapping
KIND_TO_FAMILY: dict[str, list[str]] = {}
for _fam, _kid in FAMILY_TO_KIND.items():
    KIND_TO_FAMILY.setdefault(_kid, []).append(_fam)


# ---------------------------------------------------------------------------
# Real runner execution.
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RealRunRequest:
    """Request to execute a single real OpenCode run."""
    repository_root: Path
    family_id: str
    seed: int
    mode: str  # "no_memory" | "memorix_core"
    model: str | None = None
    timeout_seconds: int = 300
    distractor_count: int = 50
    top_k: int = 10


@dataclass(frozen=True, slots=True)
class RealRunResult:
    """Result of a single real OpenCode run, adapted to new orchestrator format."""
    family_id: str
    seed: int
    mode: str
    passed: bool
    exit_code: int
    timed_out: bool
    duration_ms: float
    memory_retrieve_calls: int
    tool_calls: int
    text_events: int
    case_count: int
    passed_case_count: int
    solution_sha256: str
    stdout_preview: str
    stderr_preview: str
    error: str | None = None


def _build_task_spec(
    real_runner: Any,
    family_id: str,
    seed: int,
) -> Any:
    """Build a TaskSpec from the real runner for a given family/seed."""
    kind = FAMILY_TO_KIND.get(family_id)
    if kind is None:
        raise ValueError(f"Unknown family_id: {family_id}")
    return real_runner.build_task(kind, seed)


def run_real(
    request: RealRunRequest,
) -> RealRunResult:
    """Execute a real OpenCode run using the existing campaign runner.

    This function:
    1. Builds a TaskSpec from the real runner
    2. Creates a temporary workspace
    3. Runs OpenCode CLI via the real runner
    4. Evaluates the solution
    5. Returns an adapted RealRunResult
    """
    real_runner = _load_real_runner()

    task = _build_task_spec(real_runner, request.family_id, request.seed)

    # Create temporary workspace
    run_dir = (
        request.repository_root
        / ".benchmarks"
        / "real_runs"
        / f"{request.family_id}"
        / f"seed-{request.seed:08d}"
        / request.mode
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    workdir = run_dir / "workspace"
    workdir.mkdir(parents=True, exist_ok=True)

    # Write scaffold
    solution_path = workdir / "solution.py"
    solution_path.write_text(task.scaffold, encoding="utf-8", newline="\n")

    # Create runtime directory
    runtime_root = run_dir / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)

    # For memorix_core mode, preload memories
    if request.mode == "memorix_core":
        try:
            real_runner._preload_memory(
                runtime_root,
                [task],
                request.distractor_count,
                request.seed,
                request.top_k,
            )
        except Exception as exc:
            return RealRunResult(
                family_id=request.family_id,
                seed=request.seed,
                mode=request.mode,
                passed=False,
                exit_code=125,
                timed_out=False,
                duration_ms=0.0,
                memory_retrieve_calls=0,
                tool_calls=0,
                text_events=0,
                case_count=0,
                passed_case_count=0,
                solution_sha256="",
                stdout_preview="",
                stderr_preview=f"Memory preload failed: {exc}",
                error=f"MemoryPreloadError: {exc}",
            )

    # Execute OpenCode
    try:
        opencode_run = real_runner.run_opencode(
            repository_root=request.repository_root,
            workdir=workdir,
            runtime_root=runtime_root,
            task=task,
            mode=request.mode,
            model=request.model,
            timeout_seconds=request.timeout_seconds,
        )
    except Exception as exc:
        return RealRunResult(
            family_id=request.family_id,
            seed=request.seed,
            mode=request.mode,
            passed=False,
            exit_code=125,
            timed_out=False,
            duration_ms=0.0,
            memory_retrieve_calls=0,
            tool_calls=0,
            text_events=0,
            case_count=0,
            passed_case_count=0,
            solution_sha256="",
            stdout_preview="",
            stderr_preview=f"{type(exc).__name__}: {exc}",
            error=f"OpenCodeRunError: {exc}",
        )

    # Evaluate solution
    try:
        evaluation = real_runner.evaluate_solution(task, solution_path)
    except Exception as exc:
        evaluation = {
            "passed": False,
            "case_count": 0,
            "passed_case_count": 0,
            "error": f"EvaluationError: {exc}",
        }

    # Compute solution hash
    try:
        solution_sha = hashlib.sha256(solution_path.read_bytes()).hexdigest()
    except Exception:
        solution_sha = ""

    return RealRunResult(
        family_id=request.family_id,
        seed=request.seed,
        mode=request.mode,
        passed=bool(evaluation.get("passed", False)),
        exit_code=opencode_run.exit_code,
        timed_out=opencode_run.timed_out,
        duration_ms=opencode_run.duration_ms,
        memory_retrieve_calls=opencode_run.memory_retrieve_calls,
        tool_calls=opencode_run.tool_calls,
        text_events=opencode_run.text_events,
        case_count=int(evaluation.get("case_count", 0)),
        passed_case_count=int(evaluation.get("passed_case_count", 0)),
        solution_sha256=solution_sha,
        stdout_preview=(opencode_run.stdout or "")[:500],
        stderr_preview=(opencode_run.stderr or "")[:500],
        error=evaluation.get("error"),
    )


def run_real_pair(
    repository_root: Path,
    family_id: str,
    seed: int,
    model: str | None = None,
    timeout_seconds: int = 300,
    distractor_count: int = 50,
    top_k: int = 10,
) -> tuple[RealRunResult, RealRunResult]:
    """Execute a no_memory + memorix_core pair for a given family/seed.

    Returns (no_memory_result, memorix_core_result).
    """
    base = RealRunRequest(
        repository_root=repository_root,
        family_id=family_id,
        seed=seed,
        model=model,
        timeout_seconds=timeout_seconds,
        distractor_count=distractor_count,
        top_k=top_k,
    )

    no_memory = run_real(RealRunRequest(**{**base.__dict__, "mode": "no_memory"}))
    memorix_core = run_real(RealRunRequest(**{**base.__dict__, "mode": "memorix_core"}))

    return no_memory, memorix_core


def list_available_families() -> list[str]:
    """Return the list of family IDs that can be run with the real runner."""
    return sorted(FAMILY_TO_KIND.keys())


def validate_family_mapping() -> dict[str, str]:
    """Return the full family-to-kind mapping for inspection."""
    return dict(FAMILY_TO_KIND)
