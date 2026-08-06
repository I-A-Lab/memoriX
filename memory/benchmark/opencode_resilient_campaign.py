"""Resilient real OpenCode A/B benchmark campaign.

This module is benchmark-only. It never modifies the memoriX/OpenCode runtime.
It adds checkpointing, targeted retries, technical-failure classification,
valid-pair aggregation, and final source-integrity verification around the real
OpenCode campaign introduced in Part 40.7.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from memory.benchmark.opencode_real_campaign import (
    MODES,
    SCHEMA_VERSION,
    TASK_KINDS,
    ResolvedCampaignRequest,
    TaskSpec,
    _canonical_bytes,
    _preload_memory,
    _read_json,
    _write_json,
    build_tasks,
    compare_snapshots,
    evaluate_solution,
    protected_snapshot,
    run_opencode,
)

CAMPAIGN_VERSION = "40.8.0"

PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "large": {
        "seeds": (101, 202, 303),
        "task_count": 8,
        "distractor_count": 1000,
        "timeout_seconds": 480,
    },
    "stress": {
        "seeds": (101, 202, 303, 404, 505),
        "task_count": 8,
        "distractor_count": 1000,
        "timeout_seconds": 480,
    },
}

TRANSIENT_MARKERS = (
    "no provider available",
    "unexpected server error",
    "apierror",
    "rate limit",
    "too many requests",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "connection reset",
    "connection refused",
    "econnreset",
    "etimedout",
    "fetch failed",
    '"statuscode":429',
    '"statuscode":500',
    '"statuscode":502',
    '"statuscode":503',
    '"statuscode":504',
)

MEMORY_TOOL_PREFIXES = (
    "memory_",
    "project_",
)


@dataclass(frozen=True, slots=True)
class ResilientCampaignRequest:
    profile: str = "large"
    model: str | None = None
    seeds: tuple[int, ...] | None = None
    task_count: int | None = None
    distractor_count: int | None = None
    timeout_seconds: int | None = None
    top_k: int = 10
    max_attempts: int = 3
    retry_wait_seconds: int = 20

    def resolved(self) -> ResolvedCampaignRequest:
        if self.profile not in PROFILE_SPECS:
            raise ValueError(
                "profile must be one of: "
                + ", ".join(PROFILE_SPECS)
            )
        base = PROFILE_SPECS[self.profile]
        seeds = tuple(
            int(value)
            for value in (
                self.seeds
                if self.seeds is not None
                else base["seeds"]
            )
        )
        if not seeds:
            raise ValueError("At least one seed is required.")
        if len(set(seeds)) != len(seeds):
            raise ValueError("Duplicate seeds are not allowed.")
        task_count = int(
            self.task_count
            if self.task_count is not None
            else base["task_count"]
        )
        if task_count < 1 or task_count > len(TASK_KINDS):
            raise ValueError(
                f"task_count must be between 1 and {len(TASK_KINDS)}."
            )
        distractor_count = int(
            self.distractor_count
            if self.distractor_count is not None
            else base["distractor_count"]
        )
        if distractor_count < 0:
            raise ValueError(
                "distractor_count must be non-negative."
            )
        timeout_seconds = int(
            self.timeout_seconds
            if self.timeout_seconds is not None
            else base["timeout_seconds"]
        )
        if timeout_seconds < 30:
            raise ValueError(
                "timeout_seconds must be at least 30."
            )
        if self.top_k < 1:
            raise ValueError("top_k must be positive.")
        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts must be positive."
            )
        if self.retry_wait_seconds < 0:
            raise ValueError(
                "retry_wait_seconds must be non-negative."
            )
        model = (
            None
            if self.model is None
            else self.model.strip() or None
        )
        return ResolvedCampaignRequest(
            profile=self.profile,
            model=model,
            seeds=seeds,
            task_count=task_count,
            distractor_count=distractor_count,
            timeout_seconds=timeout_seconds,
            top_k=int(self.top_k),
        )


def _mean(values: Sequence[float]) -> float:
    return (
        round(statistics.fmean(values), 6)
        if values
        else 0.0
    )


def _parse_tools(
    stdout: str,
) -> tuple[int, tuple[str, ...]]:
    tools: list[str] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") != "tool_use":
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        tool = part.get("tool")
        if isinstance(tool, str) and tool:
            tools.append(tool)
    memory_tools = tuple(
        tool
        for tool in tools
        if tool.startswith(MEMORY_TOOL_PREFIXES)
    )
    return len(memory_tools), memory_tools


def _technical_failure_reason(
    *,
    exit_code: int,
    timed_out: bool,
    stdout: str,
    stderr: str,
    tool_calls: int,
    text_events: int,
) -> str | None:
    if exit_code == 0 and not timed_out:
        return None
    if timed_out:
        return "timeout"
    combined = (stdout + "\n" + stderr).lower()
    if any(
        marker in combined
        for marker in TRANSIENT_MARKERS
    ):
        return "provider_or_network_unavailable"
    if tool_calls == 0 and text_events == 0:
        return "cli_failed_before_agent_activity"
    return "cli_failed_after_agent_activity"


def _request_payload(
    request: ResilientCampaignRequest,
    resolved: ResolvedCampaignRequest,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "campaign_type": "resilient_real_opencode_ab",
        "profile": resolved.profile,
        "model": resolved.model,
        "seeds": list(resolved.seeds),
        "task_count": resolved.task_count,
        "distractor_count": (
            resolved.distractor_count
        ),
        "timeout_seconds": resolved.timeout_seconds,
        "top_k": resolved.top_k,
        "max_attempts": request.max_attempts,
        "retry_wait_seconds": (
            request.retry_wait_seconds
        ),
        "task_kinds": list(
            TASK_KINDS[: resolved.task_count]
        ),
    }


def _prepare_campaign(
    *,
    repository_root: Path,
    output_root: Path,
    request: ResilientCampaignRequest,
    resolved: ResolvedCampaignRequest,
    resume: bool,
) -> tuple[
    dict[str, str],
    list[TaskSpec],
    dict[int, Path],
    dict[str, dict[str, Any]],
]:
    payload = _request_payload(
        request,
        resolved,
    )
    request_path = (
        output_root
        / "campaign_request.json"
    )

    if resume:
        if not output_root.is_dir():
            raise FileNotFoundError(
                "Resume requested but output directory "
                "does not exist."
            )
        if not request_path.is_file():
            raise FileNotFoundError(
                "Resume requested but campaign_request.json "
                "is missing."
            )
        existing = _read_json(request_path)
        if existing != payload:
            raise ValueError(
                "Resume request does not match the existing "
                "campaign request."
            )
        before = _read_json(
            output_root
            / "protected_before.json"
        )
    else:
        if (
            output_root.exists()
            and any(output_root.iterdir())
        ):
            raise FileExistsError(
                "Refusing to overwrite non-empty output: "
                f"{output_root}"
            )
        output_root.mkdir(
            parents=True,
            exist_ok=True,
        )
        before = protected_snapshot(
            repository_root
        )
        _write_json(
            output_root
            / "protected_before.json",
            before,
        )
        _write_json(
            request_path,
            payload,
        )

    tasks = build_tasks(resolved)
    manifest_path = (
        output_root
        / "task_manifest.json"
    )
    manifest = {
        "tasks": [
            {
                "task_id": task.task_id,
                "seed": task.seed,
                "kind": task.kind,
                "project_id": task.project_id,
                "feature_id": task.feature_id,
                "decision_sha256": hashlib.sha256(
                    task.decision_text.encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "prompt_sha256": hashlib.sha256(
                    task.prompt.encode("utf-8")
                ).hexdigest(),
            }
            for task in tasks
        ]
    }
    if manifest_path.is_file():
        if _read_json(manifest_path) != manifest:
            raise ValueError(
                "Existing task manifest does not match."
            )
    else:
        _write_json(
            manifest_path,
            manifest,
        )

    probes_path = (
        output_root
        / "direct_memory_probes.json"
    )
    runtimes_root = (
        output_root
        / "runtimes"
    )
    runtime_by_seed: dict[int, Path] = {}

    if probes_path.is_file():
        probe_by_task = _read_json(
            probes_path
        )
        expected_ids = {
            task.task_id
            for task in tasks
        }
        if set(probe_by_task) != expected_ids:
            raise ValueError(
                "Existing direct-memory probes are incomplete."
            )
        for seed in resolved.seeds:
            runtime_by_seed[seed] = (
                runtimes_root
                / f"seed-{seed:08d}"
                / "memorix_core"
            )
    else:
        if runtimes_root.exists():
            shutil.rmtree(runtimes_root)
        probe_by_task: dict[
            str,
            dict[str, Any],
        ] = {}
        for seed in resolved.seeds:
            seed_tasks = [
                task
                for task in tasks
                if task.seed == seed
            ]
            runtime = (
                runtimes_root
                / f"seed-{seed:08d}"
                / "memorix_core"
            )
            runtime.mkdir(
                parents=True,
                exist_ok=True,
            )
            _, probes = _preload_memory(
                runtime,
                seed_tasks,
                resolved.distractor_count,
                seed,
                resolved.top_k,
            )
            runtime_by_seed[seed] = runtime
            probe_by_task.update(probes)
        _write_json(
            probes_path,
            probe_by_task,
        )

    return (
        before,
        tasks,
        runtime_by_seed,
        probe_by_task,
    )


def _existing_attempt_count(
    run_root: Path,
) -> int:
    attempts_root = run_root / "attempts"
    if not attempts_root.is_dir():
        return 0
    return len(
        [
            path
            for path in attempts_root.iterdir()
            if (
                path.is_dir()
                and path.name.startswith("attempt-")
            )
        ]
    )


def _execute_with_retries(
    *,
    repository_root: Path,
    run_root: Path,
    workdir: Path,
    runtime_root: Path,
    task: TaskSpec,
    mode: str,
    model: str | None,
    timeout_seconds: int,
    max_attempts: int,
    retry_wait_seconds: int,
) -> dict[str, Any]:
    attempts_root = run_root / "attempts"
    attempts_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    previous_count = _existing_attempt_count(
        run_root
    )
    last: dict[str, Any] | None = None

    for local_attempt in range(
        1,
        max_attempts + 1,
    ):
        attempt_number = (
            previous_count
            + local_attempt
        )
        attempt_root = (
            attempts_root
            / f"attempt-{attempt_number:02d}"
        )
        attempt_root.mkdir(
            parents=True,
            exist_ok=False,
        )

        solution_path = (
            workdir
            / "solution.py"
        )
        solution_path.write_text(
            task.scaffold,
            encoding="utf-8",
            newline="\n",
        )

        run = run_opencode(
            repository_root=repository_root,
            workdir=workdir,
            runtime_root=runtime_root,
            task=task,
            mode=mode,
            model=model,
            timeout_seconds=timeout_seconds,
        )
        memory_tool_calls, memory_tools = (
            _parse_tools(run.stdout)
        )
        reason = _technical_failure_reason(
            exit_code=run.exit_code,
            timed_out=run.timed_out,
            stdout=run.stdout,
            stderr=run.stderr,
            tool_calls=run.tool_calls,
            text_events=run.text_events,
        )
        technical_valid = reason is None

        (attempt_root / "stdout.jsonl").write_text(
            run.stdout,
            encoding="utf-8",
            newline="\n",
        )
        (attempt_root / "stderr.txt").write_text(
            run.stderr,
            encoding="utf-8",
            newline="\n",
        )

        last = {
            "exit_code": run.exit_code,
            "timed_out": run.timed_out,
            "duration_ms": run.duration_ms,
            "stdout": run.stdout,
            "stderr": run.stderr,
            "memory_retrieve_calls": (
                run.memory_retrieve_calls
            ),
            "memory_tool_calls": (
                memory_tool_calls
            ),
            "memory_tools_used": list(
                dict.fromkeys(memory_tools)
            ),
            "tool_calls": run.tool_calls,
            "text_events": run.text_events,
            "technical_valid": technical_valid,
            "technical_failure_reason": reason,
            "attempt_count": attempt_number,
            "retry_count": (
                attempt_number - 1
            ),
        }
        _write_json(
            attempt_root
            / "attempt_summary.json",
            {
                key: value
                for key, value in last.items()
                if key not in {
                    "stdout",
                    "stderr",
                }
            },
        )

        if technical_valid:
            break
        if local_attempt < max_attempts:
            delay = (
                retry_wait_seconds
                * local_attempt
            )
            if delay > 0:
                time.sleep(delay)

    if last is None:
        raise RuntimeError(
            "No OpenCode attempt was executed."
        )
    return last


def _aggregate(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for mode in MODES:
        all_rows = [
            row
            for row in rows
            if row["mode"] == mode
        ]
        valid_rows = [
            row
            for row in all_rows
            if bool(row["technical_valid"])
        ]
        case_total = sum(
            int(row["case_count"])
            for row in valid_rows
        )
        case_passed = sum(
            int(row["passed_case_count"])
            for row in valid_rows
        )
        result[mode] = {
            "run_count": len(all_rows),
            "valid_run_count": len(valid_rows),
            "technical_failure_count": (
                len(all_rows)
                - len(valid_rows)
            ),
            "task_success_rate": _mean(
                [
                    float(
                        bool(row["task_passed"])
                    )
                    for row in valid_rows
                ]
            ),
            "test_case_success_rate": (
                round(
                    case_passed
                    / case_total,
                    6,
                )
                if case_total
                else 0.0
            ),
            "cli_success_rate": _mean(
                [
                    float(
                        int(row["exit_code"])
                        == 0
                    )
                    for row in all_rows
                ]
            ),
            "timeout_rate": _mean(
                [
                    float(
                        bool(row["timed_out"])
                    )
                    for row in all_rows
                ]
            ),
            "mean_duration_ms": _mean(
                [
                    float(row["duration_ms"])
                    for row in valid_rows
                ]
            ),
            "mean_tool_calls": _mean(
                [
                    float(row["tool_calls"])
                    for row in valid_rows
                ]
            ),
            "memory_retrieve_call_rate": _mean(
                [
                    float(
                        int(
                            row[
                                "memory_retrieve_calls"
                            ]
                        )
                        > 0
                    )
                    for row in valid_rows
                ]
            ),
            "memory_tool_call_rate": _mean(
                [
                    float(
                        int(
                            row[
                                "memory_tool_calls"
                            ]
                        )
                        > 0
                    )
                    for row in valid_rows
                ]
            ),
            "retried_run_count": sum(
                int(row["retry_count"]) > 0
                for row in all_rows
            ),
            "total_attempt_count": sum(
                int(row["attempt_count"])
                for row in all_rows
            ),
        }

    pairs: dict[
        tuple[int, str],
        dict[str, Mapping[str, Any]],
    ] = {}
    for row in rows:
        pairs.setdefault(
            (
                int(row["seed"]),
                str(row["kind"]),
            ),
            {},
        )[str(row["mode"])] = row

    memory_wins = 0
    no_memory_wins = 0
    ties = 0
    valid_pair_count = 0
    invalid_pair_count = 0

    for pair in pairs.values():
        if set(pair) != set(MODES):
            invalid_pair_count += 1
            continue
        if not all(
            bool(pair[mode]["technical_valid"])
            for mode in MODES
        ):
            invalid_pair_count += 1
            continue
        valid_pair_count += 1
        no_score = int(
            pair["no_memory"][
                "passed_case_count"
            ]
        )
        memory_score = int(
            pair["memorix_core"][
                "passed_case_count"
            ]
        )
        if memory_score > no_score:
            memory_wins += 1
        elif no_score > memory_score:
            no_memory_wins += 1
        else:
            ties += 1

    result["paired_comparison"] = {
        "expected_pair_count": len(pairs),
        "valid_pair_count": valid_pair_count,
        "invalid_pair_count": invalid_pair_count,
        "memorix_wins": memory_wins,
        "no_memory_wins": no_memory_wins,
        "ties": ties,
    }
    return result


def _write_rows(
    output_root: Path,
    rows: Sequence[Mapping[str, Any]],
) -> tuple[Path, Path]:
    jsonl_path = (
        output_root
        / "opencode_resilient_runs.jsonl"
    )
    with jsonl_path.open("wb") as handle:
        for row in rows:
            handle.write(
                _canonical_bytes(row)
            )

    csv_path = (
        output_root
        / "opencode_resilient_runs.csv"
    )
    fieldnames = sorted(
        {
            key
            for row in rows
            for key in row
        }
    )
    with csv_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        for row in rows:
            serializable = dict(row)
            serializable[
                "memory_tools_used"
            ] = ";".join(
                row.get(
                    "memory_tools_used",
                    [],
                )
            )
            writer.writerow(serializable)
    return jsonl_path, csv_path


def run_resilient_campaign(
    *,
    repository_root: Path,
    output_root: Path,
    archive_path: Path,
    request: ResilientCampaignRequest,
    resume: bool = False,
) -> dict[str, Any]:
    repository_root = (
        repository_root.resolve()
    )
    output_root = output_root.resolve()
    archive_path = archive_path.resolve()
    resolved = request.resolved()

    if (
        output_root == repository_root
        or repository_root
        in output_root.parents
    ):
        raise ValueError(
            "Campaign output must be outside "
            "the repository."
        )
    if (
        archive_path == repository_root
        or repository_root
        in archive_path.parents
    ):
        raise ValueError(
            "Campaign archive must be outside "
            "the repository."
        )
    if archive_path.exists():
        raise FileExistsError(
            f"Archive already exists: {archive_path}"
        )

    (
        before,
        tasks,
        runtime_by_seed,
        probe_by_task,
    ) = _prepare_campaign(
        repository_root=repository_root,
        output_root=output_root,
        request=request,
        resolved=resolved,
        resume=resume,
    )

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for task_index, task in enumerate(tasks):
        mode_order = (
            MODES
            if (
                task_index
                + task.seed
            )
            % 2
            == 0
            else tuple(reversed(MODES))
        )
        for mode in mode_order:
            run_root = (
                output_root
                / "runs"
                / f"seed-{task.seed:08d}"
                / task.kind
                / mode
            )
            workdir = (
                run_root
                / "workspace"
            )
            workdir.mkdir(
                parents=True,
                exist_ok=True,
            )
            summary_path = (
                run_root
                / "run_summary.json"
            )

            if summary_path.is_file():
                existing = _read_json(
                    summary_path
                )
                if bool(
                    existing.get(
                        "technical_valid"
                    )
                ):
                    rows.append(existing)
                    continue

            _write_json(
                run_root
                / "task_public.json",
                {
                    "task_id": task.task_id,
                    "seed": task.seed,
                    "kind": task.kind,
                    "project_id": task.project_id,
                    "feature_id": task.feature_id,
                    "prompt": task.prompt,
                },
            )
            runtime = (
                runtime_by_seed[task.seed]
                if mode == "memorix_core"
                else run_root
                / "empty_runtime"
            )
            runtime.mkdir(
                parents=True,
                exist_ok=True,
            )

            execution = (
                _execute_with_retries(
                    repository_root=repository_root,
                    run_root=run_root,
                    workdir=workdir,
                    runtime_root=runtime,
                    task=task,
                    mode=mode,
                    model=resolved.model,
                    timeout_seconds=(
                        resolved.timeout_seconds
                    ),
                    max_attempts=(
                        request.max_attempts
                    ),
                    retry_wait_seconds=(
                        request.retry_wait_seconds
                    ),
                )
            )

            (
                run_root
                / "stdout.jsonl"
            ).write_text(
                str(execution["stdout"]),
                encoding="utf-8",
                newline="\n",
            )
            (
                run_root
                / "stderr.txt"
            ).write_text(
                str(execution["stderr"]),
                encoding="utf-8",
                newline="\n",
            )

            solution_path = (
                workdir
                / "solution.py"
            )
            if execution[
                "technical_valid"
            ]:
                evaluation = evaluate_solution(
                    task,
                    solution_path,
                )
            else:
                evaluation = {
                    "passed": False,
                    "case_count": 0,
                    "passed_case_count": 0,
                    "cases": [],
                    "technical_failure": (
                        execution[
                            "technical_failure_reason"
                        ]
                    ),
                }
            _write_json(
                run_root
                / "hidden_evaluation.json",
                evaluation,
            )

            probe = probe_by_task.get(
                task.task_id,
                {},
            )
            row = {
                "task_id": task.task_id,
                "seed": task.seed,
                "kind": task.kind,
                "mode": mode,
                "agent": "default_primary",
                "model": (
                    resolved.model
                    or "<configured-default>"
                ),
                "distractor_count": (
                    resolved.distractor_count
                    if mode == "memorix_core"
                    else 0
                ),
                "exit_code": execution[
                    "exit_code"
                ],
                "timed_out": execution[
                    "timed_out"
                ],
                "duration_ms": execution[
                    "duration_ms"
                ],
                "memory_retrieve_calls": (
                    execution[
                        "memory_retrieve_calls"
                    ]
                ),
                "memory_tool_calls": (
                    execution[
                        "memory_tool_calls"
                    ]
                ),
                "memory_tools_used": (
                    execution[
                        "memory_tools_used"
                    ]
                ),
                "tool_calls": execution[
                    "tool_calls"
                ],
                "text_events": execution[
                    "text_events"
                ],
                "technical_valid": (
                    execution[
                        "technical_valid"
                    ]
                ),
                "technical_failure_reason": (
                    execution[
                        "technical_failure_reason"
                    ]
                ),
                "attempt_count": execution[
                    "attempt_count"
                ],
                "retry_count": execution[
                    "retry_count"
                ],
                "task_passed": evaluation[
                    "passed"
                ],
                "case_count": evaluation[
                    "case_count"
                ],
                "passed_case_count": evaluation[
                    "passed_case_count"
                ],
                "direct_exact_hit": (
                    bool(
                        probe.get(
                            "exact",
                            {},
                        ).get("hit")
                    )
                    if mode
                    == "memorix_core"
                    else None
                ),
                "direct_exact_rank": (
                    probe.get(
                        "exact",
                        {},
                    ).get("rank")
                    if mode
                    == "memorix_core"
                    else None
                ),
                "direct_paraphrase_hit": (
                    bool(
                        probe.get(
                            "paraphrase",
                            {},
                        ).get("hit")
                    )
                    if mode
                    == "memorix_core"
                    else None
                ),
                "direct_paraphrase_rank": (
                    probe.get(
                        "paraphrase",
                        {},
                    ).get("rank")
                    if mode
                    == "memorix_core"
                    else None
                ),
                "solution_sha256": (
                    hashlib.sha256(
                        solution_path.read_bytes()
                    ).hexdigest()
                ),
            }
            rows.append(row)
            _write_json(
                summary_path,
                row,
            )

    after = protected_snapshot(
        repository_root
    )
    differences = compare_snapshots(
        before,
        after,
    )
    protected_unchanged = not any(
        differences.values()
    )
    _write_json(
        output_root
        / "protected_after.json",
        after,
    )
    _write_json(
        output_root
        / "protected_diff.json",
        differences,
    )

    aggregate = _aggregate(rows)
    jsonl_path, csv_path = _write_rows(
        output_root,
        rows,
    )
    technical_failure_count = sum(
        not bool(row["technical_valid"])
        for row in rows
    )
    expected_run_count = (
        len(tasks)
        * len(MODES)
    )
    completed = (
        len(rows) == expected_run_count
        and technical_failure_count == 0
        and protected_unchanged
    )

    memory_rows = [
        row
        for row in rows
        if row["mode"] == "memorix_core"
    ]
    report = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "campaign_type": (
            "resilient_real_opencode_ab"
        ),
        "completed": completed,
        "resume_supported": True,
        "request": _request_payload(
            request,
            resolved,
        ),
        "task_count": len(tasks),
        "expected_run_count": (
            expected_run_count
        ),
        "run_count": len(rows),
        "technical_failure_count": (
            technical_failure_count
        ),
        "aggregates": aggregate,
        "direct_memory_probe": {
            "exact_hit_rate": _mean(
                [
                    float(
                        bool(
                            row[
                                "direct_exact_hit"
                            ]
                        )
                    )
                    for row in memory_rows
                ]
            ),
            "paraphrase_hit_rate": _mean(
                [
                    float(
                        bool(
                            row[
                                "direct_paraphrase_hit"
                            ]
                        )
                    )
                    for row in memory_rows
                ]
            ),
        },
        "protected_core_unchanged": (
            protected_unchanged
        ),
        "protected_core_differences": (
            differences
        ),
        "total_duration_ms": round(
            (
                time.perf_counter()
                - started
            )
            * 1000.0,
            3,
        ),
        "artifacts": {
            "runs_jsonl": jsonl_path.name,
            "runs_csv": csv_path.name,
            "runs_directory": "runs",
            "runtimes_directory": "runtimes",
            "direct_memory_probes": (
                "direct_memory_probes.json"
            ),
            "protected_before": (
                "protected_before.json"
            ),
            "protected_after": (
                "protected_after.json"
            ),
            "protected_diff": (
                "protected_diff.json"
            ),
        },
    }
    report_path = (
        output_root
        / "opencode_resilient_campaign_report.json"
    )
    _write_json(
        report_path,
        report,
    )

    if not protected_unchanged:
        raise RuntimeError(
            "Protected source files changed. "
            "Results were preserved for audit."
        )
    if technical_failure_count > 0:
        raise RuntimeError(
            f"{technical_failure_count} technical run(s) "
            "remain invalid after retries. Re-run the "
            "same command with --resume; completed runs "
            "will be skipped."
        )
    if len(rows) != expected_run_count:
        raise RuntimeError(
            "Campaign is incomplete. Re-run the same "
            "command with --resume."
        )

    archive_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    created = Path(
        shutil.make_archive(
            str(
                archive_path.with_suffix(
                    ""
                )
            ),
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


def validate_resilient_report(
    path: Path,
) -> dict[str, Any]:
    report = _read_json(path)
    if (
        report.get("schema_version")
        != SCHEMA_VERSION
    ):
        raise ValueError(
            "Invalid schema_version."
        )
    if (
        report.get("campaign_version")
        != CAMPAIGN_VERSION
    ):
        raise ValueError(
            "Invalid campaign_version."
        )
    if (
        report.get("campaign_type")
        != "resilient_real_opencode_ab"
    ):
        raise ValueError(
            "Invalid campaign_type."
        )
    if report.get("completed") is not True:
        raise ValueError(
            "Campaign is not complete."
        )
    if (
        int(
            report.get(
                "technical_failure_count",
                -1,
            )
        )
        != 0
    ):
        raise ValueError(
            "Technical failures remain."
        )
    if (
        report.get(
            "protected_core_unchanged"
        )
        is not True
    ):
        raise ValueError(
            "Protected core changed."
        )
    task_count = int(
        report.get("task_count", -1)
    )
    expected = int(
        report.get(
            "expected_run_count",
            -1,
        )
    )
    actual = int(
        report.get("run_count", -1)
    )
    if (
        task_count < 1
        or expected
        != task_count * 2
        or actual != expected
    ):
        raise ValueError(
            "Invalid task/run counts."
        )
    paired = (
        report.get(
            "aggregates",
            {},
        ).get(
            "paired_comparison",
            {},
        )
    )
    if (
        int(
            paired.get(
                "invalid_pair_count",
                -1,
            )
        )
        != 0
    ):
        raise ValueError(
            "Invalid A/B pairs remain."
        )
    return report
