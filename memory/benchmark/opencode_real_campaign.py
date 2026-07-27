"""Real, graduated A/B benchmark for OpenCode with and without memoriX.

This module is deliberately isolated from the runtime implementation. It only
creates benchmark workspaces outside the repository, preloads validated memories
through the public gateway, runs the real OpenCode CLI, evaluates hidden tests,
and verifies that protected source files did not change.
"""
from __future__ import annotations

import csv
import gc
import hashlib
import importlib.util
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CAMPAIGN_VERSION = "40.7.3"
SCHEMA_VERSION = 1
MODES = ("no_memory", "memorix_core")
TASK_KINDS = (
    "csv_delimiter",
    "username_separator",
    "retry_schedule",
    "date_format",
    "cache_key",
    "page_size",
    "boolean_tokens",
    "filename_policy",
)

PROFILE_SPECS: dict[str, dict[str, Any]] = {
    "smoke": {
        "seeds": (101,),
        "task_count": 2,
        "distractor_count": 10,
        "timeout_seconds": 240,
    },
    "small": {
        "seeds": (101, 202, 303),
        "task_count": 4,
        "distractor_count": 50,
        "timeout_seconds": 300,
    },
    "medium": {
        "seeds": (101, 202, 303),
        "task_count": 8,
        "distractor_count": 250,
        "timeout_seconds": 360,
    },
    "stress": {
        "seeds": (101, 202, 303, 404, 505),
        "task_count": 8,
        "distractor_count": 1000,
        "timeout_seconds": 480,
    },
}

PROTECTED_PATHS = (
    "memory/gateway",
    "memory/hot_site",
    "memory/cold_site",
    "memory/consolidation",
    "memory/adaptive",
    "scripts/memorix_mcp_server.py",
    "packages/opencode/src/memorix",
    "packages/opencode/src/tool",
    ".opencode/plugins/memorix.ts",
)


@dataclass(frozen=True, slots=True)
class CampaignRequest:
    profile: str
    model: str | None
    seeds: tuple[int, ...] | None = None
    task_count: int | None = None
    distractor_count: int | None = None
    timeout_seconds: int | None = None
    top_k: int = 10

    def resolved(self) -> "ResolvedCampaignRequest":
        if self.profile not in PROFILE_SPECS:
            raise ValueError(
                "profile must be one of: " + ", ".join(PROFILE_SPECS)
            )
        base = PROFILE_SPECS[self.profile]
        seeds = tuple(int(value) for value in (self.seeds or base["seeds"]))
        if not seeds:
            raise ValueError("At least one seed is required.")
        if len(set(seeds)) != len(seeds):
            raise ValueError("Duplicate seeds are not allowed.")
        if any(seed < 0 for seed in seeds):
            raise ValueError("Seeds must be non-negative.")
        task_count = int(self.task_count or base["task_count"])
        if task_count < 1 or task_count > len(TASK_KINDS):
            raise ValueError(
                f"task_count must be between 1 and {len(TASK_KINDS)}."
            )
        distractor_count = int(
            base["distractor_count"]
            if self.distractor_count is None
            else self.distractor_count
        )
        if distractor_count < 0:
            raise ValueError("distractor_count must be non-negative.")
        timeout_seconds = int(self.timeout_seconds or base["timeout_seconds"])
        if timeout_seconds < 30:
            raise ValueError("timeout_seconds must be at least 30.")
        if self.top_k < 1:
            raise ValueError("top_k must be positive.")
        model = None if self.model is None else self.model.strip()
        if model == "":
            model = None
        return ResolvedCampaignRequest(
            profile=self.profile,
            model=model,
            seeds=seeds,
            task_count=task_count,
            distractor_count=distractor_count,
            timeout_seconds=timeout_seconds,
            top_k=int(self.top_k),
        )


@dataclass(frozen=True, slots=True)
class ResolvedCampaignRequest:
    profile: str
    model: str | None
    seeds: tuple[int, ...]
    task_count: int
    distractor_count: int
    timeout_seconds: int
    top_k: int


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    seed: int
    kind: str
    project_id: str
    feature_id: str
    decision_text: str
    prompt: str
    scaffold: str
    expected: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OpenCodeRun:
    exit_code: int
    timed_out: bool
    duration_ms: float
    stdout: str
    stderr: str
    memory_retrieve_calls: int
    tool_calls: int
    text_events: int


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            "Refusing to overwrite non-empty real campaign directory: "
            f"{path}"
        )
    path.mkdir(parents=True, exist_ok=True)


def _stable_token(seed: int, kind: str, suffix: str) -> str:
    return hashlib.sha256(
        f"{seed}|{kind}|{suffix}".encode("utf-8")
    ).hexdigest()[:12]


def build_task(kind: str, seed: int) -> TaskSpec:
    if kind not in TASK_KINDS:
        raise ValueError(f"Unsupported task kind: {kind}")
    rng = random.Random(f"{seed}|{kind}|40.7")
    token = _stable_token(seed, kind, "task")
    project_id = f"bench-{kind}-{seed}-{token[:6]}"
    feature_id = f"feature-{token[6:]}"

    if kind == "csv_delimiter":
        delimiter = rng.choice([";", "|", "\t"])
        expected = {"delimiter": delimiter}
        decision = (
            f"For feature {feature_id}, serialize table cells with delimiter "
            f"{delimiter!r}, join rows with a single LF, and do not add a trailing LF."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def serialize_rows(rows: list[list[object]]) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement serialize_rows(rows). Convert every cell with str(), join cells "
            "using the previously validated delimiter, join rows with one LF, and do "
            "not append a trailing LF."
        )
    elif kind == "username_separator":
        separator = rng.choice(["-", "_", "."])
        expected = {"separator": separator}
        decision = (
            f"For feature {feature_id}, normalized usernames use {separator!r} between "
            "words. Trim, lowercase, collapse whitespace and repeated separators."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def normalize_username(value: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement normalize_username(value). Trim and lowercase the input, replace "
            "runs of whitespace with the previously validated separator, and collapse "
            "repeated occurrences of that separator."
        )
    elif kind == "retry_schedule":
        base = rng.choice([0.1, 0.25, 0.5])
        factor = rng.choice([1.5, 2.0, 3.0])
        expected = {"base": base, "factor": factor}
        decision = (
            f"For feature {feature_id}, retry delay starts at {base} seconds and is "
            f"multiplied by {factor} after each attempt. Round each delay to 3 decimals."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def retry_delays(attempts: int) -> list[float]:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement retry_delays(attempts). Return an empty list for attempts <= 0. "
            "Otherwise use the previously validated initial delay and multiplier and "
            "round every value to three decimals."
        )
    elif kind == "date_format":
        fmt = rng.choice(["%d/%m/%Y", "%Y-%m-%d", "%m.%d.%Y"])
        expected = {"format": fmt}
        decision = (
            f"For feature {feature_id}, display calendar dates with strftime format "
            f"{fmt!r}."
        )
        scaffold = (
            "from __future__ import annotations\n"
            "from datetime import date\n\n"
            "def format_date(value: date) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement format_date(value) using the previously validated project date "
            "format. The input is datetime.date."
        )
    elif kind == "cache_key":
        separator = rng.choice(["::", ":", "|"])
        expected = {"separator": separator}
        decision = (
            f"For feature {feature_id}, cache keys join a trimmed lowercase namespace "
            f"and a trimmed identifier with separator {separator!r}."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def build_cache_key(namespace: str, identifier: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement build_cache_key(namespace, identifier). Trim both values, lowercase "
            "the namespace only, and join them with the previously validated separator."
        )
    elif kind == "page_size":
        default = rng.choice([20, 25, 30])
        maximum = rng.choice([80, 100, 120])
        expected = {"default": default, "maximum": maximum}
        decision = (
            f"For feature {feature_id}, pagination defaults to {default} items and clamps "
            f"requested values to the inclusive range 1..{maximum}."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def normalize_page_size(requested: int | None) -> int:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement normalize_page_size(requested). Use the previously validated default "
            "when requested is None and clamp numeric values to the previously validated "
            "inclusive range."
        )
    elif kind == "boolean_tokens":
        variants = [
            ("true", "yes", "1"),
            ("enabled", "on", "yes"),
            ("active", "true", "y"),
        ]
        tokens = rng.choice(variants)
        expected = {"true_tokens": list(tokens)}
        decision = (
            f"For feature {feature_id}, parse a value as enabled only when its trimmed "
            f"lowercase form is one of {list(tokens)!r}."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def parse_enabled(value: object) -> bool:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement parse_enabled(value). Convert the value to string, trim and lowercase "
            "it, then use the previously validated set of true tokens. All other values "
            "return False."
        )
    else:
        separator = rng.choice(["-", "_", "."])
        lowercase = rng.choice([True, False])
        expected = {"separator": separator, "lowercase": lowercase}
        case_rule = "lowercase the stem" if lowercase else "preserve the stem's letter case"
        decision = (
            f"For feature {feature_id}, artifact filenames replace whitespace with "
            f"{separator!r}, collapse repeats, {case_rule}, and normalize the extension "
            "to lowercase without a leading dot."
        )
        scaffold = (
            "from __future__ import annotations\n\n"
            "def artifact_filename(name: str, extension: str) -> str:\n"
            "    raise NotImplementedError\n"
        )
        behavior = (
            "Implement artifact_filename(name, extension). Trim the name, replace whitespace "
            "with the previously validated separator, collapse repeated separators, apply "
            "the previously validated case rule, normalize extension to lowercase without "
            "a leading dot, and return stem.extension."
        )

    prompt = (
        f"Work only in solution.py for project {project_id}, feature {feature_id}.\n"
        f"{behavior}\n"
        "A durable implementation decision for this project was validated in a previous "
        "session. Use any available validated project memory before coding. Do not ask the "
        "user to repeat the decision. Do not create notes, comments, specification files, "
        "or tests that reveal the decision. Implement the function completely and keep the "
        "public signature unchanged."
    )
    return TaskSpec(
        task_id=f"task-{kind}-{seed}-{token}",
        seed=seed,
        kind=kind,
        project_id=project_id,
        feature_id=feature_id,
        decision_text=decision,
        prompt=prompt,
        scaffold=scaffold,
        expected=expected,
    )


def build_tasks(request: ResolvedCampaignRequest) -> list[TaskSpec]:
    return [
        build_task(kind, seed)
        for seed in request.seeds
        for kind in TASK_KINDS[: request.task_count]
    ]


def _load_solution(path: Path) -> Any:
    module_name = "memorix_benchmark_solution_" + hashlib.sha256(
        str(path).encode("utf-8")
    ).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load solution module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_solution(task: TaskSpec, solution_path: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    try:
        module = _load_solution(solution_path)
        if task.kind == "csv_delimiter":
            delimiter = str(task.expected["delimiter"])
            raw_cases = [
                ([["a", "b"], [1, 2]], f"a{delimiter}b\n1{delimiter}2"),
                ([], ""),
                ([["single"]], "single"),
            ]
            for args, expected in raw_cases:
                actual = module.serialize_rows(args)
                cases.append({"expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "username_separator":
            sep = str(task.expected["separator"])
            raw_cases = [
                ("  Alice   Smith  ", f"alice{sep}smith"),
                (f"BOB{sep}{sep}Jones", f"bob{sep}jones"),
                ("Single", "single"),
            ]
            for value, expected in raw_cases:
                actual = module.normalize_username(value)
                cases.append({"input": value, "expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "retry_schedule":
            base = float(task.expected["base"])
            factor = float(task.expected["factor"])
            raw_cases = [0, 1, 4]
            for attempts in raw_cases:
                expected = [round(base * (factor ** index), 3) for index in range(max(0, attempts))]
                actual = module.retry_delays(attempts)
                cases.append({"input": attempts, "expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "date_format":
            fmt = str(task.expected["format"])
            for value in [date(2026, 7, 24), date(2030, 1, 5)]:
                expected = value.strftime(fmt)
                actual = module.format_date(value)
                cases.append({"input": value.isoformat(), "expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "cache_key":
            sep = str(task.expected["separator"])
            raw_cases = [
                ((" Users ", " 42 "), f"users{sep}42"),
                (("API", "ABC-9"), f"api{sep}ABC-9"),
            ]
            for args, expected in raw_cases:
                actual = module.build_cache_key(*args)
                cases.append({"input": list(args), "expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "page_size":
            default = int(task.expected["default"])
            maximum = int(task.expected["maximum"])
            raw_cases = [(None, default), (0, 1), (1, 1), (maximum + 50, maximum), (17, 17)]
            for value, expected in raw_cases:
                actual = module.normalize_page_size(value)
                cases.append({"input": value, "expected": expected, "actual": actual, "passed": actual == expected})
        elif task.kind == "boolean_tokens":
            true_tokens = {str(value).lower() for value in task.expected["true_tokens"]}
            values = list(true_tokens) + [" TRUE ", "false", "0", "disabled", "random"]
            for value in values:
                expected = str(value).strip().lower() in true_tokens
                actual = module.parse_enabled(value)
                cases.append({"input": value, "expected": expected, "actual": actual, "passed": actual is expected})
        elif task.kind == "filename_policy":
            sep = str(task.expected["separator"])
            lowercase = bool(task.expected["lowercase"])
            raw_cases = [(" My  Report ", ".PDF"), ("Alpha Beta", "TXT")]
            for name, extension in raw_cases:
                import re

                stem = re.sub(r"\s+", sep, name.strip())
                stem = re.sub(re.escape(sep) + r"+", sep, stem)
                if lowercase:
                    stem = stem.lower()
                expected = f"{stem}.{extension.lstrip('.').lower()}"
                actual = module.artifact_filename(name, extension)
                cases.append({"input": [name, extension], "expected": expected, "actual": actual, "passed": actual == expected})
        else:
            raise ValueError(f"Unsupported task kind: {task.kind}")
    except Exception as exc:
        return {
            "passed": False,
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case.get("passed")),
            "cases": cases,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }
    passed_count = sum(1 for case in cases if bool(case["passed"]))
    return {
        "passed": bool(cases) and passed_count == len(cases),
        "case_count": len(cases),
        "passed_case_count": passed_count,
        "cases": cases,
        "error": None,
        "traceback": None,
    }


def _iter_protected_files(repository_root: Path) -> Iterable[Path]:
    for relative in PROTECTED_PATHS:
        target = repository_root / relative
        if target.is_file():
            yield target
        elif target.is_dir():
            for path in sorted(target.rglob("*")):
                if not path.is_file():
                    continue
                if "__pycache__" in path.parts:
                    continue
                if path.suffix in {".pyc", ".pyo"}:
                    continue
                yield path


def protected_snapshot(repository_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in _iter_protected_files(repository_root):
        relative = path.relative_to(repository_root).as_posix()
        snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not snapshot:
        raise ValueError("No protected source files were found.")
    return snapshot


def compare_snapshots(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    return {
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": sorted(
            key for key in before_keys & after_keys if before[key] != after[key]
        ),
    }


def _preload_memory(
    runtime_root: Path,
    tasks: Sequence[TaskSpec],
    distractor_count: int,
    seed: int,
    top_k: int,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    from memory.data import MemoryStoragePaths
    from memory.gateway.public_api import MemoriXGateway

    gateway = MemoriXGateway(
        storage_paths=MemoryStoragePaths.from_runtime_root(runtime_root),
        titan_top_k=max(5, top_k),
        titan_min_score=0.0,
    )
    memory_ids: dict[str, str] = {}
    probes: dict[str, dict[str, Any]] = {}

    for task in tasks:
        candidate = gateway.propose_memory_candidate(
            content=(
                f"Validated project decision. Project {task.project_id}. "
                f"Feature {task.feature_id}. {task.decision_text}"
            ),
            reason="real OpenCode benchmark fixture",
            source_event_ids=(task.task_id,),
            importance=0.95,
            confidence=1.0,
            surprise=0.5,
            metadata={
                "subject": f"{task.project_id} {task.feature_id}",
                "original_content": task.decision_text,
                "tags": [
                    "benchmark-40.7",
                    task.project_id,
                    task.feature_id,
                    task.kind,
                ],
                "benchmark_task_id": task.task_id,
                "benchmark_seed": seed,
            },
        )
        validated = gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="benchmark-human-fixture",
            validation_reason="controlled benchmark decision",
        )
        memory_ids[task.task_id] = validated.memory_id

    rng = random.Random(f"{seed}|distractors|40.7")
    separators = [";", "|", "\t", "-", "_", ".", "::", ":"]
    for index in range(distractor_count):
        kind = rng.choice(TASK_KINDS)
        fake_project = f"noise-project-{seed}-{index:05d}"
        fake_feature = f"noise-feature-{rng.randrange(10_000, 99_999)}"
        fake_value = rng.choice(separators)
        candidate = gateway.propose_memory_candidate(
            content=(
                f"Validated project decision. Project {fake_project}. Feature "
                f"{fake_feature}. Use convention {fake_value!r} for unrelated "
                f"{kind} work."
            ),
            reason="hard distractor fixture",
            source_event_ids=(f"noise-{seed}-{index}",),
            importance=0.7,
            confidence=1.0,
            surprise=0.2,
            metadata={
                "subject": f"{fake_project} {fake_feature}",
                "original_content": f"Use convention {fake_value!r} for {kind}.",
                "tags": ["benchmark-40.7", fake_project, fake_feature, kind],
                "benchmark_distractor": True,
            },
        )
        gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="benchmark-human-fixture",
            validation_reason="controlled benchmark distractor",
        )

    for task in tasks:
        expected_id = memory_ids[task.task_id]
        queries = {
            "exact": (
                f"validated decision project {task.project_id} feature "
                f"{task.feature_id} {task.kind}"
            ),
            "paraphrase": (
                f"What convention was approved for {task.feature_id} in project "
                f"{task.project_id}?"
            ),
        }
        task_probe: dict[str, Any] = {}
        for label, query in queries.items():
            result = gateway.retrieve_memory(query, top_k=top_k)
            ids = [match.memory_id for match in result.matches]
            rank = next(
                (index + 1 for index, value in enumerate(ids) if value == expected_id),
                None,
            )
            task_probe[label] = {
                "query": query,
                "expected_memory_id": expected_id,
                "retrieved_memory_ids": ids,
                "rank": rank,
                "hit": rank is not None,
            }
        probes[task.task_id] = task_probe

    del gateway
    gc.collect()
    return memory_ids, probes


def _parse_opencode_events(stdout: str) -> tuple[int, int, int]:
    memory_calls = 0
    tool_calls = 0
    text_events = 0
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
        event_type = event.get("type")
        if event_type == "text":
            text_events += 1
        if event_type == "tool_use":
            tool_calls += 1
            part = event.get("part")
            if isinstance(part, dict) and part.get("tool") == "memory_retrieve":
                memory_calls += 1
    return memory_calls, tool_calls, text_events


def run_opencode(
    *,
    repository_root: Path,
    workdir: Path,
    runtime_root: Path,
    task: TaskSpec,
    mode: str,
    model: str | None,
    timeout_seconds: int,
) -> OpenCodeRun:
    if mode not in MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    bun = shutil.which("bun")
    if bun is None:
        raise FileNotFoundError("bun executable was not found in PATH.")
    cli_entry = repository_root / "packages" / "opencode" / "src" / "index.ts"
    if not cli_entry.is_file():
        raise FileNotFoundError(f"OpenCode CLI entry is missing: {cli_entry}")

    args = [
        bun,
        "run",
        "--conditions=browser",
        str(cli_entry),
        "run",
        "--pure",
        "--format",
        "json",
        "--dir",
        str(workdir),
        "--dangerously-skip-permissions",
        "--title",
        f"memoriX benchmark {task.task_id} {mode}",
    ]
    if model is not None:
        args.extend(["--model", model])
    args.append(task.prompt)

    env = dict(os.environ)
    env.update(
        {
            "MEMORIX_BENCHMARK_MODE": mode,
            "MEMORIX_ENABLED": "true" if mode == "memorix_core" else "false",
            "MEMORIX_PYTHON_EXECUTABLE": sys.executable,
            "MEMORIX_RUNTIME_ROOT": str(runtime_root),
            "MEMORIX_TIMEOUT_MS": "120000",
            "MEMORIX_TITAN_D_MODEL": "256",
            "MEMORIX_TITAN_HIDDEN_DIM": "256",
            "MEMORIX_TITAN_MAX_ITEMS": "50000",
            "MEMORIX_TITAN_DEVICE": "cpu",
            "MEMORIX_TITAN_TOP_K": "10",
            "MEMORIX_TITAN_MIN_SCORE": "0.0",
            "MEMORIX_HOOK_CAPTURE_MESSAGES": "false",
            "MEMORIX_HOOK_CAPTURE_TOOL_RESULTS": "false",
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_DISABLE_AUTOCOMPACT": "1",
        }
    )

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            args,
            cwd=repository_root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        timed_out = False
        exit_code = int(completed.returncode)
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout = "" if exc.stdout is None else str(exc.stdout)
        stderr = "" if exc.stderr is None else str(exc.stderr)
    duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
    memory_calls, tool_calls, text_events = _parse_opencode_events(stdout)
    return OpenCodeRun(
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr,
        memory_retrieve_calls=memory_calls,
        tool_calls=tool_calls,
        text_events=text_events,
    )


def _mean(values: Sequence[float]) -> float:
    return round(statistics.fmean(values), 6) if values else 0.0


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mode in MODES:
        mode_rows = [row for row in rows if row["mode"] == mode]
        task_rate = _mean([float(bool(row["task_passed"])) for row in mode_rows])
        case_total = sum(int(row["case_count"]) for row in mode_rows)
        case_passed = sum(int(row["passed_case_count"]) for row in mode_rows)
        result[mode] = {
            "run_count": len(mode_rows),
            "task_success_rate": task_rate,
            "test_case_success_rate": round(case_passed / case_total, 6) if case_total else 0.0,
            "cli_success_rate": _mean([float(int(row["exit_code"]) == 0) for row in mode_rows]),
            "timeout_rate": _mean([float(bool(row["timed_out"])) for row in mode_rows]),
            "mean_duration_ms": _mean([float(row["duration_ms"]) for row in mode_rows]),
            "mean_tool_calls": _mean([float(row["tool_calls"]) for row in mode_rows]),
            "memory_retrieve_call_rate": _mean(
                [float(int(row["memory_retrieve_calls"]) > 0) for row in mode_rows]
            ),
        }
    pairs: dict[tuple[int, str], dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        pairs.setdefault((int(row["seed"]), str(row["kind"])), {})[str(row["mode"])] = row
    memory_wins = 0
    no_memory_wins = 0
    ties = 0
    complete_pairs = 0
    for pair in pairs.values():
        if set(pair) != set(MODES):
            continue
        complete_pairs += 1
        no_score = int(pair["no_memory"]["passed_case_count"])
        memory_score = int(pair["memorix_core"]["passed_case_count"])
        if memory_score > no_score:
            memory_wins += 1
        elif no_score > memory_score:
            no_memory_wins += 1
        else:
            ties += 1
    result["paired_comparison"] = {
        "pair_count": complete_pairs,
        "memorix_wins": memory_wins,
        "no_memory_wins": no_memory_wins,
        "ties": ties,
    }
    return result


def run_campaign(
    *,
    repository_root: Path,
    output_root: Path,
    archive_path: Path,
    request: CampaignRequest,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    output_root = output_root.resolve()
    archive_path = archive_path.resolve()
    resolved = request.resolved()

    if output_root == repository_root or repository_root in output_root.parents:
        raise ValueError("Campaign output must be outside the repository.")
    if archive_path == repository_root or repository_root in archive_path.parents:
        raise ValueError("Campaign archive must be outside the repository.")
    if archive_path.exists():
        raise FileExistsError(f"Archive already exists: {archive_path}")
    _ensure_empty(output_root)

    before = protected_snapshot(repository_root)
    _write_json(output_root / "protected_before.json", before)
    tasks = build_tasks(resolved)
    _write_json(
        output_root / "campaign_request.json",
        {
            "schema_version": SCHEMA_VERSION,
            "campaign_version": CAMPAIGN_VERSION,
            **asdict(resolved),
            "task_kinds": list(TASK_KINDS[: resolved.task_count]),
        },
    )
    _write_json(
        output_root / "task_manifest.json",
        {
            "tasks": [
                {
                    "task_id": task.task_id,
                    "seed": task.seed,
                    "kind": task.kind,
                    "project_id": task.project_id,
                    "feature_id": task.feature_id,
                    "decision_sha256": hashlib.sha256(
                        task.decision_text.encode("utf-8")
                    ).hexdigest(),
                    "prompt_sha256": hashlib.sha256(task.prompt.encode("utf-8")).hexdigest(),
                }
                for task in tasks
            ]
        },
    )

    task_by_seed: dict[int, list[TaskSpec]] = {
        seed: [task for task in tasks if task.seed == seed]
        for seed in resolved.seeds
    }
    runtime_by_seed: dict[int, Path] = {}
    probe_by_task: dict[str, dict[str, Any]] = {}
    for seed, seed_tasks in task_by_seed.items():
        runtime = output_root / "runtimes" / f"seed-{seed:08d}" / "memorix_core"
        runtime.mkdir(parents=True, exist_ok=True)
        _, probes = _preload_memory(
            runtime,
            seed_tasks,
            resolved.distractor_count,
            seed,
            resolved.top_k,
        )
        runtime_by_seed[seed] = runtime
        probe_by_task.update(probes)
    _write_json(output_root / "direct_memory_probes.json", probe_by_task)

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for task_index, task in enumerate(tasks):
        mode_order = MODES if (task_index + task.seed) % 2 == 0 else tuple(reversed(MODES))
        for mode in mode_order:
            run_root = (
                output_root
                / "runs"
                / f"seed-{task.seed:08d}"
                / task.kind
                / mode
            )
            workdir = run_root / "workspace"
            workdir.mkdir(parents=True, exist_ok=True)
            solution_path = workdir / "solution.py"
            solution_path.write_text(
                task.scaffold,
                encoding="utf-8",
                newline="\n",
            )
            _write_json(
                run_root / "task_public.json",
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
                else run_root / "empty_runtime"
            )
            runtime.mkdir(parents=True, exist_ok=True)
            try:
                opencode_run = run_opencode(
                    repository_root=repository_root,
                    workdir=workdir,
                    runtime_root=runtime,
                    task=task,
                    mode=mode,
                    model=resolved.model,
                    timeout_seconds=resolved.timeout_seconds,
                )
            except Exception as exc:
                opencode_run = OpenCodeRun(
                    exit_code=125,
                    timed_out=False,
                    duration_ms=0.0,
                    stdout="",
                    stderr=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                    memory_retrieve_calls=0,
                    tool_calls=0,
                    text_events=0,
                )
            (run_root / "stdout.jsonl").write_text(
                opencode_run.stdout,
                encoding="utf-8",
                newline="\n",
            )
            (run_root / "stderr.txt").write_text(
                opencode_run.stderr,
                encoding="utf-8",
                newline="\n",
            )
            evaluation = evaluate_solution(task, solution_path)
            _write_json(run_root / "hidden_evaluation.json", evaluation)
            probe = probe_by_task.get(task.task_id, {})
            row = {
                "task_id": task.task_id,
                "seed": task.seed,
                "kind": task.kind,
                "mode": mode,
                "agent": "default_primary",
                "model": resolved.model or "<configured-default>",
                "distractor_count": resolved.distractor_count if mode == "memorix_core" else 0,
                "exit_code": opencode_run.exit_code,
                "timed_out": opencode_run.timed_out,
                "duration_ms": opencode_run.duration_ms,
                "memory_retrieve_calls": opencode_run.memory_retrieve_calls,
                "tool_calls": opencode_run.tool_calls,
                "text_events": opencode_run.text_events,
                "task_passed": evaluation["passed"],
                "case_count": evaluation["case_count"],
                "passed_case_count": evaluation["passed_case_count"],
                "direct_exact_hit": bool(probe.get("exact", {}).get("hit")) if mode == "memorix_core" else None,
                "direct_exact_rank": probe.get("exact", {}).get("rank") if mode == "memorix_core" else None,
                "direct_paraphrase_hit": bool(probe.get("paraphrase", {}).get("hit")) if mode == "memorix_core" else None,
                "direct_paraphrase_rank": probe.get("paraphrase", {}).get("rank") if mode == "memorix_core" else None,
                "solution_sha256": hashlib.sha256(solution_path.read_bytes()).hexdigest(),
            }
            rows.append(row)
            _write_json(run_root / "run_summary.json", row)

    aggregate = _aggregate(rows)
    after = protected_snapshot(repository_root)
    differences = compare_snapshots(before, after)
    protected_unchanged = not any(differences.values())
    _write_json(output_root / "protected_after.json", after)
    _write_json(output_root / "protected_diff.json", differences)

    rows_jsonl = output_root / "opencode_ab_runs.jsonl"
    with rows_jsonl.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))
    rows_csv = output_root / "opencode_ab_runs.csv"
    fieldnames = sorted({key for row in rows for key in row})
    with rows_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    memory_rows = [row for row in rows if row["mode"] == "memorix_core"]
    report = {
        "schema_version": SCHEMA_VERSION,
        "campaign_version": CAMPAIGN_VERSION,
        "campaign_type": "real_opencode_ab",
        "agent": "default_primary",
        "model_selection": (
            "configured_default"
            if resolved.model is None
            else "explicit"
        ),
        "request": asdict(resolved),
        "task_count": len(tasks),
        "run_count": len(rows),
        "aggregates": aggregate,
        "direct_memory_probe": {
            "exact_hit_rate": _mean([float(bool(row["direct_exact_hit"])) for row in memory_rows]),
            "paraphrase_hit_rate": _mean([float(bool(row["direct_paraphrase_hit"])) for row in memory_rows]),
        },
        "protected_core_unchanged": protected_unchanged,
        "protected_core_differences": differences,
        "total_duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "artifacts": {
            "runs_jsonl": rows_jsonl.name,
            "runs_csv": rows_csv.name,
            "direct_memory_probes": "direct_memory_probes.json",
            "protected_before": "protected_before.json",
            "protected_after": "protected_after.json",
            "protected_diff": "protected_diff.json",
            "runs_directory": "runs",
            "runtimes_directory": "runtimes",
        },
    }
    report_path = output_root / "opencode_real_campaign_report.json"
    _write_json(report_path, report)

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

    if not protected_unchanged:
        raise RuntimeError(
            "Protected memoriX/OpenCode source files changed during the campaign. "
            "Results were preserved for audit."
        )
    return report


def validate_campaign_report(path: Path) -> dict[str, Any]:
    report = _read_json(path)
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version.")
    if report.get("campaign_version") != CAMPAIGN_VERSION:
        raise ValueError("Invalid campaign_version.")
    if report.get("campaign_type") != "real_opencode_ab":
        raise ValueError("Invalid campaign_type.")
    request = report.get("request")
    if not isinstance(request, dict):
        raise ValueError("Invalid request.")
    task_count = int(report.get("task_count", -1))
    run_count = int(report.get("run_count", -1))
    if task_count < 1 or run_count != task_count * 2:
        raise ValueError("Invalid task or run count.")
    if report.get("protected_core_unchanged") is not True:
        raise ValueError("Protected core was not unchanged.")
    aggregates = report.get("aggregates")
    if not isinstance(aggregates, dict):
        raise ValueError("Invalid aggregates.")
    for mode in MODES:
        if mode not in aggregates:
            raise ValueError(f"Missing mode aggregate: {mode}")
    return report
