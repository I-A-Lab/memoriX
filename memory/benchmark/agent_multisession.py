"""Deterministic multi-session agent benchmark for no_memory vs memorix_core."""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from memory.benchmark.memory_pure_benchmark import (
    DeterministicLexicalEngine,
    MemoriXGatewayEngine,
    RetrievalEngine,
)

AGENT_BENCHMARK_VERSION = "35.1"
OFFICIAL_MODES = ("no_memory", "memorix_core")
OFFICIAL_BACKENDS = ("lexical", "memorix")


@dataclass(frozen=True, slots=True)
class AgentMetrics:
    query_count: int
    task_success_rate: float
    prior_information_reuse_rate: float
    forbidden_information_use_rate: float
    session_resume_success_rate: float
    exact_value_rate: float
    turn_count: int
    tool_call_count: int
    mean_response_ms: float
    p95_response_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SessionAgent(Protocol):
    def learn(self, records: Sequence[Mapping[str, Any]]) -> int: ...
    def start_new_session(self) -> None: ...
    def answer(self, query: Mapping[str, Any], *, top_k: int) -> Sequence[Mapping[str, Any]]: ...


class NoMemoryAgent:
    """Session-only context. Starting a new session intentionally clears all facts."""

    def __init__(self) -> None:
        self._session_records: list[dict[str, Any]] = []

    def learn(self, records: Sequence[Mapping[str, Any]]) -> int:
        self._session_records = [dict(item) for item in records]
        return 0

    def start_new_session(self) -> None:
        self._session_records = []

    def answer(self, query: Mapping[str, Any], *, top_k: int) -> Sequence[Mapping[str, Any]]:
        if not self._session_records:
            return []
        engine = DeterministicLexicalEngine()
        engine.ingest(self._session_records)
        return engine.retrieve(str(query["query"]), top_k=top_k)


class PersistentMemoryAgent:
    """Agent facade backed by one persistent retrieval engine across sessions."""

    def __init__(self, engine: RetrievalEngine) -> None:
        self._engine = engine

    def learn(self, records: Sequence[Mapping[str, Any]]) -> int:
        eligible = [
            dict(item)
            for item in records
            if bool(item.get("active")) and bool(item.get("should_retrieve"))
        ]
        self._engine.ingest(eligible)
        return len(eligible)

    def start_new_session(self) -> None:
        return None

    def answer(self, query: Mapping[str, Any], *, top_k: int) -> Sequence[Mapping[str, Any]]:
        return self._engine.retrieve(str(query["query"]), top_k=top_k)


def build_agent(*, mode: str, backend: str, runtime_root: Path | None = None) -> SessionAgent:
    if mode not in OFFICIAL_MODES:
        raise ValueError(f"Unsupported mode: {mode}")
    if backend not in OFFICIAL_BACKENDS:
        raise ValueError(f"Unsupported backend: {backend}")
    if mode == "no_memory":
        return NoMemoryAgent()
    if backend == "lexical":
        return PersistentMemoryAgent(DeterministicLexicalEngine())
    if runtime_root is None:
        raise ValueError("memorix backend requires runtime_root.")
    return PersistentMemoryAgent(MemoriXGatewayEngine(runtime_root.resolve()))


def run_agent_multisession_benchmark(
    dataset_dir: Path,
    agent: SessionAgent,
    *,
    top_k: int = 5,
) -> tuple[AgentMetrics, list[dict[str, Any]]]:
    if top_k < 1:
        raise ValueError("top_k must be positive.")
    records = _read_jsonl(dataset_dir / "records.jsonl")
    queries = _read_jsonl(dataset_dir / "queries.jsonl")
    if not queries:
        raise ValueError("Dataset has no queries.")

    store_tool_calls = agent.learn(records)
    agent.start_new_session()

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for turn_index, query in enumerate(queries, start=1):
        started = time.perf_counter_ns()
        matches = list(agent.answer(query, top_k=top_k))
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        latencies.append(elapsed)

        retrieved_ids = [str(item.get("record_id", "")) for item in matches]
        expected_ids = [str(item) for item in query.get("expected_record_ids", [])]
        forbidden_ids = [str(item) for item in query.get("forbidden_record_ids", [])]
        success = bool(expected_ids) and any(item in expected_ids for item in retrieved_ids)
        forbidden_use = any(item in forbidden_ids for item in retrieved_ids)
        expected_value = query.get("expected_value")
        exact_value = expected_value is None or any(
            str((item.get("canonical_fact") or {}).get("value")) == str(expected_value)
            for item in matches
        )
        if not expected_ids:
            success = not forbidden_use

        rows.append(
            {
                "turn_index": turn_index,
                "session_index": 2,
                "query_id": str(query["query_id"]),
                "family": str(query["family"]),
                "expected_record_ids": expected_ids,
                "forbidden_record_ids": forbidden_ids,
                "retrieved_record_ids": retrieved_ids,
                "success": bool(success),
                "forbidden_information_used": bool(forbidden_use),
                "exact_value": bool(exact_value),
                "response_ms": elapsed,
            }
        )

    count = len(rows)
    successful = sum(bool(row["success"]) for row in rows)
    forbidden = sum(bool(row["forbidden_information_used"]) for row in rows)
    exact = sum(bool(row["exact_value"]) for row in rows)
    metrics = AgentMetrics(
        query_count=count,
        task_success_rate=successful / count,
        prior_information_reuse_rate=successful / count,
        forbidden_information_use_rate=forbidden / count,
        session_resume_success_rate=successful / count,
        exact_value_rate=exact / count,
        turn_count=count + 2,
        tool_call_count=store_tool_calls + count,
        mean_response_ms=sum(latencies) / count,
        p95_response_ms=_percentile(latencies, 0.95),
    )
    return metrics, rows


def write_agent_results(
    output_dir: Path,
    metrics: AgentMetrics,
    rows: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    backend: str,
    dataset_id: str,
) -> Path:
    output = output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty result directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    rows_path = output / "agent_episode_results.jsonl"
    rows_path.write_text(
        "".join(
            json.dumps(dict(row), sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )
    payload = {
        "schema_version": 1,
        "benchmark_version": AGENT_BENCHMARK_VERSION,
        "suite": "agent_multisession",
        "mode": mode,
        "backend": backend,
        "dataset_id": dataset_id,
        "metrics": metrics.to_dict(),
        "episode_results_sha256": hashlib.sha256(rows_path.read_bytes()).hexdigest(),
    }
    report_path = output / "agent_report.json"
    report_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report_path


def validate_agent_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported agent report schema_version.")
    if payload.get("benchmark_version") != AGENT_BENCHMARK_VERSION:
        raise ValueError("Unsupported agent benchmark_version.")
    if payload.get("mode") not in OFFICIAL_MODES:
        raise ValueError("Invalid benchmark mode.")
    if payload.get("backend") not in OFFICIAL_BACKENDS:
        raise ValueError("Invalid benchmark backend.")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object.")
    for name in (
        "task_success_rate",
        "prior_information_reuse_rate",
        "forbidden_information_use_rate",
        "session_resume_success_rate",
        "exact_value_rate",
    ):
        value = float(metrics[name])
        if value < 0 or value > 1:
            raise ValueError(f"{name} must be between 0 and 1.")
    digest = str(payload.get("episode_results_sha256", ""))
    if len(digest) != 64:
        raise ValueError("episode_results_sha256 must contain 64 characters.")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL line {number} must contain an object.")
        rows.append(payload)
    return rows


def _percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return float(ordered[index])
