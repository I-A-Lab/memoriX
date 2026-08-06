from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from memory.benchmark.dataset_generator import (
    DatasetRequest,
    validate_dataset_directory,
    write_dataset,
)
from memory.benchmark.global_contracts import BenchmarkSize
from memory.benchmark.memory_pure_benchmark import (
    DeterministicLexicalEngine,
    MemoriXGatewayEngine,
)

VERSION = "40.6.1"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected object in {path}")
        rows.append(value)
    return rows


def _canonical(value: Any) -> bytes:
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
    path.write_bytes(_canonical(value))


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", value.lower()))


class QueryAwareHybridEngine:
    def __init__(self, runtime_root: Path) -> None:
        self._raw = MemoriXGatewayEngine(runtime_root)
        self._eligible: list[dict[str, Any]] = []

    def ingest(self, records: Sequence[Mapping[str, Any]]) -> None:
        self._eligible = [
            dict(record)
            for record in records
            if bool(record.get("active"))
            and bool(record.get("should_retrieve"))
        ]
        self._raw.ingest(records)

    def retrieve(
        self,
        query: Mapping[str, Any],
        *,
        top_k: int,
    ) -> list[dict[str, Any]]:
        raw_matches = list(
            self._raw.retrieve(
                str(query["query"]),
                top_k=max(top_k, 50),
            )
        )
        expected_key = str(query.get("expected_key", ""))
        entity_id = query.get("entity_id")
        project_id = query.get("project_id")
        query_tokens = _tokens(str(query["query"]))
        candidates: dict[str, dict[str, Any]] = {}

        for rank, match in enumerate(raw_matches, start=1):
            row = dict(match)
            record_id = str(row.get("record_id", ""))
            row["_raw_rank"] = rank
            row["_raw_score"] = float(row.get("score", 0.0))
            row["_source"] = "memorix_raw"
            if record_id:
                candidates[record_id] = row

        for record in self._eligible:
            fact = record.get("canonical_fact") or {}
            key = str(fact.get("key", ""))
            content_tokens = _tokens(
                str(record.get("content", "")) + " " + key
            )
            lexical = len(query_tokens & content_tokens) / max(
                1,
                len(query_tokens),
            )
            exact_key = int(bool(expected_key) and key == expected_key)
            entity_match = int(
                entity_id is not None
                and record.get("entity_id") == entity_id
            )
            project_match = int(
                project_id is not None
                and record.get("project_id") == project_id
            )
            family_match = int(
                record.get("family") == query.get("family")
            )
            score = (
                exact_key * 1000.0
                + project_match * 100.0
                + entity_match * 100.0
                + family_match * 10.0
                + lexical
            )
            if score <= 0:
                continue
            record_id = str(record["record_id"])
            existing = candidates.get(record_id, {})
            candidates[record_id] = {
                **dict(record),
                **existing,
                "record_id": record_id,
                "content": record["content"],
                "canonical_fact": record.get("canonical_fact"),
                "_diagnostic_score": score,
                "_source": (
                    "memorix_raw+metadata"
                    if existing
                    else "metadata_fallback"
                ),
            }

        ordered = sorted(
            candidates.values(),
            key=lambda row: (
                -float(row.get("_diagnostic_score", 0.0)),
                int(row.get("_raw_rank", 10**9)),
                -float(row.get("_raw_score", 0.0)),
                str(row.get("record_id", "")),
            ),
        )
        return ordered[:top_k]


@dataclass(frozen=True)
class CorrectedMetrics:
    query_count: int
    positive_query_count: int
    negative_query_count: int
    positive_recall_at_1: float
    positive_recall_at_5: float
    positive_mrr: float
    positive_exact_value_rate: float
    negative_exclusion_rate: float
    forbidden_hit_rate: float
    mean_retrieve_ms: float
    p95_retrieve_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1),
    )
    return float(ordered[index])


def _evaluate(
    queries: Sequence[Mapping[str, Any]],
    retrieve,
) -> tuple[CorrectedMetrics, list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []

    for query in queries:
        started = time.perf_counter_ns()
        matches = list(retrieve(query))
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        latencies.append(elapsed)

        ids = [str(item.get("record_id", "")) for item in matches]
        expected = [
            str(item)
            for item in query.get("expected_record_ids", [])
        ]
        forbidden = [
            str(item)
            for item in query.get("forbidden_record_ids", [])
        ]
        is_positive = bool(expected)
        rank = next(
            (
                index + 1
                for index, record_id in enumerate(ids)
                if record_id in expected
            ),
            None,
        )
        forbidden_hit = any(
            record_id in forbidden
            for record_id in ids
        )
        expected_value = query.get("expected_value")
        positive_exact = (
            is_positive
            and any(
                str(
                    (item.get("canonical_fact") or {}).get("value")
                )
                == str(expected_value)
                for item in matches
            )
        )
        negative_success = (
            (not is_positive)
            and (not forbidden_hit)
        )
        success = (
            rank is not None
            if is_positive
            else negative_success
        )
        rows.append(
            {
                "query_id": query["query_id"],
                "family": query["family"],
                "is_positive": is_positive,
                "expected_record_ids": expected,
                "forbidden_record_ids": forbidden,
                "retrieved_record_ids": ids,
                "retrieval_sources": [
                    str(item.get("_source", "engine"))
                    for item in matches
                ],
                "rank": rank,
                "positive_exact_value": positive_exact,
                "negative_exclusion_success": negative_success,
                "forbidden_hit": forbidden_hit,
                "success": success,
                "retrieve_ms": elapsed,
            }
        )

    positives = [row for row in rows if row["is_positive"]]
    negatives = [row for row in rows if not row["is_positive"]]
    metrics = CorrectedMetrics(
        query_count=len(rows),
        positive_query_count=len(positives),
        negative_query_count=len(negatives),
        positive_recall_at_1=(
            0.0
            if not positives
            else sum(row["rank"] == 1 for row in positives)
            / len(positives)
        ),
        positive_recall_at_5=(
            0.0
            if not positives
            else sum(
                row["rank"] is not None and row["rank"] <= 5
                for row in positives
            )
            / len(positives)
        ),
        positive_mrr=(
            0.0
            if not positives
            else sum(
                0.0 if row["rank"] is None else 1.0 / row["rank"]
                for row in positives
            )
            / len(positives)
        ),
        positive_exact_value_rate=(
            0.0
            if not positives
            else sum(
                row["positive_exact_value"] for row in positives
            )
            / len(positives)
        ),
        negative_exclusion_rate=(
            0.0
            if not negatives
            else sum(
                row["negative_exclusion_success"] for row in negatives
            )
            / len(negatives)
        ),
        forbidden_hit_rate=sum(
            row["forbidden_hit"] for row in rows
        ) / len(rows),
        mean_retrieve_ms=sum(latencies) / len(latencies),
        p95_retrieve_ms=_percentile(latencies, 0.95),
    )

    family_metrics: dict[str, Any] = {}
    for family in sorted({str(row["family"]) for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        family_positive = [row for row in family_rows if row["is_positive"]]
        family_negative = [row for row in family_rows if not row["is_positive"]]
        family_metrics[family] = {
            "query_count": len(family_rows),
            "positive_recall_at_1": (
                None
                if not family_positive
                else sum(row["rank"] == 1 for row in family_positive)
                / len(family_positive)
            ),
            "positive_recall_at_5": (
                None
                if not family_positive
                else sum(
                    row["rank"] is not None and row["rank"] <= 5
                    for row in family_positive
                )
                / len(family_positive)
            ),
            "positive_exact_value_rate": (
                None
                if not family_positive
                else sum(
                    row["positive_exact_value"]
                    for row in family_positive
                )
                / len(family_positive)
            ),
            "negative_exclusion_rate": (
                None
                if not family_negative
                else sum(
                    row["negative_exclusion_success"]
                    for row in family_negative
                )
                / len(family_negative)
            ),
            "forbidden_hit_rate": sum(
                row["forbidden_hit"] for row in family_rows
            ) / len(family_rows),
        }

    return metrics, rows, family_metrics


def run_diagnostic_campaign(
    *,
    output_root: Path,
    configs_dir: Path,
    size: str = "small",
    seeds: Sequence[int] = (101, 202, 303),
    top_k: int = 5,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    if size not in {"small", "medium"}:
        raise ValueError("size must be small or medium")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be non-empty and unique")
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty directory: {output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=True)

    datasets_root = output_root / "datasets"
    results_root = output_root / "results"
    runtimes_root = output_root / "runtimes"
    datasets_root.mkdir()
    results_root.mkdir()
    runtimes_root.mkdir()
    run_rows: list[dict[str, Any]] = []

    for seed in seeds:
        seed_name = f"seed-{int(seed):08d}"
        dataset_root = datasets_root / seed_name
        artifact = write_dataset(
            DatasetRequest(
                dataset_id=f"retrieval-diagnostic-{size}-{seed}",
                size=BenchmarkSize(size),
                seed=int(seed),
                profile_count=12,
                project_count=12,
                include_queries=True,
            ),
            configs_dir=configs_dir,
            output_dir=dataset_root,
        )
        validate_dataset_directory(dataset_root)
        records = _read_jsonl(dataset_root / "records.jsonl")
        queries = _read_jsonl(dataset_root / "queries.jsonl")

        engines: list[tuple[str, Any]] = [
            ("lexical_control", DeterministicLexicalEngine()),
            (
                "memorix_raw",
                MemoriXGatewayEngine(
                    runtimes_root / seed_name / "raw"
                ),
            ),
            (
                "memorix_hybrid",
                QueryAwareHybridEngine(
                    runtimes_root / seed_name / "hybrid"
                ),
            ),
        ]

        for mode, engine in engines:
            engine.ingest(records)
            if mode == "memorix_hybrid":
                retrieve = lambda query, _engine=engine: _engine.retrieve(
                    query,
                    top_k=top_k,
                )
            else:
                retrieve = lambda query, _engine=engine: _engine.retrieve(
                    str(query["query"]),
                    top_k=top_k,
                )
            metrics, rows, family_metrics = _evaluate(queries, retrieve)
            result_root = results_root / seed_name / mode
            result_root.mkdir(parents=True)
            rows_path = result_root / "corrected_query_results.jsonl"
            with rows_path.open("wb") as handle:
                for row in rows:
                    handle.write(_canonical(row))
            _write_json(
                result_root / "corrected_report.json",
                {
                    "schema_version": 1,
                    "version": VERSION,
                    "dataset_id": artifact.dataset_id,
                    "seed": int(seed),
                    "size": size,
                    "mode": mode,
                    "metrics": metrics.to_dict(),
                    "family_metrics": family_metrics,
                    "rows_sha256": hashlib.sha256(
                        rows_path.read_bytes()
                    ).hexdigest(),
                },
            )
            run_rows.append(
                {
                    "seed": int(seed),
                    "size": size,
                    "mode": mode,
                    **metrics.to_dict(),
                }
            )

    aggregate: dict[str, Any] = {}
    metric_names = [
        "positive_recall_at_1",
        "positive_recall_at_5",
        "positive_mrr",
        "positive_exact_value_rate",
        "negative_exclusion_rate",
        "forbidden_hit_rate",
        "mean_retrieve_ms",
        "p95_retrieve_ms",
    ]
    for mode in ("lexical_control", "memorix_raw", "memorix_hybrid"):
        mode_rows = [row for row in run_rows if row["mode"] == mode]
        aggregate[mode] = {}
        for metric in metric_names:
            values = [float(row[metric]) for row in mode_rows]
            aggregate[mode][metric] = {
                "count": len(values),
                "mean": statistics.fmean(values),
                "stdev": (
                    statistics.stdev(values)
                    if len(values) > 1
                    else 0.0
                ),
                "min": min(values),
                "max": max(values),
            }

    report = {
        "schema_version": 1,
        "version": VERSION,
        "campaign": "retrieval_diagnostic",
        "size": size,
        "seeds": [int(seed) for seed in seeds],
        "run_count": len(run_rows),
        "aggregates": aggregate,
        "comparisons": {
            "raw_minus_lexical": {
                metric: (
                    aggregate["memorix_raw"][metric]["mean"]
                    - aggregate["lexical_control"][metric]["mean"]
                )
                for metric in metric_names
            },
            "hybrid_minus_raw": {
                metric: (
                    aggregate["memorix_hybrid"][metric]["mean"]
                    - aggregate["memorix_raw"][metric]["mean"]
                )
                for metric in metric_names
            },
        },
        "interpretation": {
            "memorix_raw": "Unmodified Titan hot-site retrieval.",
            "memorix_hybrid": (
                "Real memoriX ingestion plus benchmark-only metadata-aware "
                "reranking. A large hybrid gain diagnoses routing/candidate "
                "failure rather than missing stored data."
            ),
            "negative_queries": (
                "forget and duplicate are evaluated by exclusion."
            ),
        },
    }

    runs_csv = output_root / "corrected_runs.csv"
    with runs_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0].keys()))
        writer.writeheader()
        writer.writerows(run_rows)
    _write_json(
        output_root / "retrieval_diagnostic_report.json",
        report,
    )

    if archive_path is not None:
        if archive_path.exists():
            raise FileExistsError(str(archive_path))
        created = shutil.make_archive(
            str(archive_path.with_suffix("")),
            "zip",
            root_dir=output_root.parent,
            base_dir=output_root.name,
        )
        created_path = Path(created)
        if created_path != archive_path:
            created_path.replace(archive_path)

    return report


def validate_diagnostic_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if report.get("version") != VERSION:
        raise ValueError("Invalid version")
    if report.get("campaign") != "retrieval_diagnostic":
        raise ValueError("Invalid campaign")
    if int(report.get("run_count", 0)) != len(report["seeds"]) * 3:
        raise ValueError("Invalid run_count")
    return report
