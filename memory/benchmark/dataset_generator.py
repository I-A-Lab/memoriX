"""Deterministic, versioned datasets for the global memoriX benchmark."""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from memory.benchmark.global_contracts import (
    BENCHMARK_ID,
    SCHEMA_VERSION,
    BenchmarkSize,
    load_benchmark_contracts,
)

DATASET_SCHEMA_VERSION = 1
DATASET_GENERATOR_VERSION = "32.1"
_DATASET_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

FAMILIES: tuple[str, ...] = (
    "user_profile",
    "project_fact",
    "code_decision",
    "contradiction",
    "update",
    "forget",
    "duplicate",
    "temporal",
    "distractor",
)

_TARGET_FAMILIES = FAMILIES[:-1]
_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class DatasetRequest:
    dataset_id: str
    size: BenchmarkSize
    seed: int
    profile_count: int
    project_count: int
    include_queries: bool = True

    def validate(self) -> None:
        if not _DATASET_ID_PATTERN.fullmatch(self.dataset_id):
            raise ValueError("dataset_id contains unsupported characters.")
        if self.seed < 0:
            raise ValueError("seed must be non-negative.")
        if self.profile_count <= 0:
            raise ValueError("profile_count must be positive.")
        if self.project_count <= 0:
            raise ValueError("project_count must be positive.")


@dataclass(frozen=True, slots=True)
class DatasetArtifact:
    schema_version: int
    benchmark_id: str
    dataset_id: str
    generator_version: str
    size: str
    seed: int
    record_count: int
    query_count: int
    family_counts: Mapping[str, int]
    records_sha256: str
    queries_sha256: str | None
    request_sha256: str
    records_file: str
    queries_file: str | None

    def validate(self) -> None:
        if self.schema_version != DATASET_SCHEMA_VERSION:
            raise ValueError("Unsupported dataset schema_version.")
        if self.benchmark_id != BENCHMARK_ID:
            raise ValueError("Invalid benchmark_id.")
        if not _DATASET_ID_PATTERN.fullmatch(self.dataset_id):
            raise ValueError("Invalid dataset_id.")
        if self.generator_version != DATASET_GENERATOR_VERSION:
            raise ValueError("Unsupported generator_version.")
        if self.record_count <= 0:
            raise ValueError("record_count must be positive.")
        if self.query_count < 0:
            raise ValueError("query_count must be non-negative.")
        if sum(int(value) for value in self.family_counts.values()) != self.record_count:
            raise ValueError("family_counts do not sum to record_count.")
        if set(self.family_counts) != set(FAMILIES):
            raise ValueError("family_counts must contain every official family.")
        if not _SHA256_PATTERN.fullmatch(self.records_sha256):
            raise ValueError("records_sha256 must be a SHA-256 digest.")
        if self.queries_sha256 is not None and not _SHA256_PATTERN.fullmatch(
            self.queries_sha256
        ):
            raise ValueError("queries_sha256 must be a SHA-256 digest.")
        if not _SHA256_PATTERN.fullmatch(self.request_sha256):
            raise ValueError("request_sha256 must be a SHA-256 digest.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_dataset_request(path: Path) -> DatasetRequest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise ValueError("Unsupported dataset request schema_version.")
    if payload.get("benchmark_id") != BENCHMARK_ID:
        raise ValueError("Invalid benchmark_id in dataset request.")
    request = DatasetRequest(
        dataset_id=str(payload["dataset_id"]),
        size=BenchmarkSize(str(payload["size"])),
        seed=int(payload["seed"]),
        profile_count=int(payload["profile_count"]),
        project_count=int(payload["project_count"]),
        include_queries=bool(payload.get("include_queries", True)),
    )
    request.validate()
    return request


def request_sha256(request: DatasetRequest) -> str:
    payload = asdict(request)
    payload["size"] = request.size.value
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def generate_dataset(
    request: DatasetRequest,
    *,
    configs_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    request.validate()
    contracts = load_benchmark_contracts(configs_dir)
    size_contract = next(
        (item for item in contracts.sizes if item.size is request.size),
        None,
    )
    if size_contract is None:
        raise ValueError(f"Unknown benchmark size: {request.size.value}")

    rng = random.Random(request.seed)
    target_counts = _balanced_counts(size_contract.memory_count, len(_TARGET_FAMILIES))
    records: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []

    for family, count in zip(_TARGET_FAMILIES, target_counts, strict=True):
        for index in range(count):
            record, query = _build_target_record(
                family=family,
                index=index,
                request=request,
                rng=rng,
            )
            records.append(record)
            if request.include_queries and query is not None:
                queries.append(query)

    for index in range(size_contract.distractor_count):
        records.append(_build_distractor(index=index, request=request, rng=rng))

    records.sort(key=lambda item: item["record_id"])
    queries.sort(key=lambda item: item["query_id"])
    _validate_generated_records(records, queries, request, size_contract.memory_count)
    return records, queries


def write_dataset(
    request: DatasetRequest,
    *,
    configs_dir: Path,
    output_dir: Path,
) -> DatasetArtifact:
    output = output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty dataset directory: {output}")
    output.mkdir(parents=True, exist_ok=True)

    records, queries = generate_dataset(request, configs_dir=configs_dir)
    records_path = output / "records.jsonl"
    queries_path = output / "queries.jsonl"
    manifest_path = output / "dataset_manifest.json"

    records_bytes = _jsonl_bytes(records)
    records_path.write_bytes(records_bytes)

    queries_bytes: bytes | None = None
    queries_name: str | None = None
    queries_digest: str | None = None
    if request.include_queries:
        queries_bytes = _jsonl_bytes(queries)
        queries_path.write_bytes(queries_bytes)
        queries_name = queries_path.name
        queries_digest = hashlib.sha256(queries_bytes).hexdigest()

    counts = {family: 0 for family in FAMILIES}
    for record in records:
        counts[record["family"]] += 1

    artifact = DatasetArtifact(
        schema_version=DATASET_SCHEMA_VERSION,
        benchmark_id=BENCHMARK_ID,
        dataset_id=request.dataset_id,
        generator_version=DATASET_GENERATOR_VERSION,
        size=request.size.value,
        seed=request.seed,
        record_count=len(records),
        query_count=len(queries) if request.include_queries else 0,
        family_counts=counts,
        records_sha256=hashlib.sha256(records_bytes).hexdigest(),
        queries_sha256=queries_digest,
        request_sha256=request_sha256(request),
        records_file=records_path.name,
        queries_file=queries_name,
    )
    artifact.validate()
    manifest_path.write_text(
        json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return artifact


def validate_dataset_directory(path: Path) -> DatasetArtifact:
    root = path.resolve()
    manifest_path = root / "dataset_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("dataset_manifest.json is missing.")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact = DatasetArtifact(
        schema_version=int(payload["schema_version"]),
        benchmark_id=str(payload["benchmark_id"]),
        dataset_id=str(payload["dataset_id"]),
        generator_version=str(payload["generator_version"]),
        size=str(payload["size"]),
        seed=int(payload["seed"]),
        record_count=int(payload["record_count"]),
        query_count=int(payload["query_count"]),
        family_counts={str(k): int(v) for k, v in payload["family_counts"].items()},
        records_sha256=str(payload["records_sha256"]),
        queries_sha256=(
            None if payload.get("queries_sha256") is None else str(payload["queries_sha256"])
        ),
        request_sha256=str(payload["request_sha256"]),
        records_file=str(payload["records_file"]),
        queries_file=(None if payload.get("queries_file") is None else str(payload["queries_file"])),
    )
    artifact.validate()

    records_path = root / artifact.records_file
    if not records_path.is_file():
        raise FileNotFoundError("records file is missing.")
    records_bytes = records_path.read_bytes()
    if hashlib.sha256(records_bytes).hexdigest() != artifact.records_sha256:
        raise ValueError("records_sha256 mismatch.")
    records = _read_jsonl(records_path)
    if len(records) != artifact.record_count:
        raise ValueError("record_count does not match records file.")

    queries: list[dict[str, Any]] = []
    if artifact.queries_file is not None:
        queries_path = root / artifact.queries_file
        if not queries_path.is_file():
            raise FileNotFoundError("queries file is missing.")
        queries_bytes = queries_path.read_bytes()
        if hashlib.sha256(queries_bytes).hexdigest() != artifact.queries_sha256:
            raise ValueError("queries_sha256 mismatch.")
        queries = _read_jsonl(queries_path)
    if len(queries) != artifact.query_count:
        raise ValueError("query_count does not match queries file.")

    _validate_generated_records(records, queries, None, None)
    return artifact


def _balanced_counts(total: int, bucket_count: int) -> list[int]:
    if total < bucket_count:
        raise ValueError(
            f"memory_count={total} is too small for {bucket_count} target families."
        )
    base, remainder = divmod(total, bucket_count)
    return [base + (1 if index < remainder else 0) for index in range(bucket_count)]


def _build_target_record(
    *, family: str, index: int, request: DatasetRequest, rng: random.Random
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    profile_index = index % request.profile_count
    project_index = index % request.project_count
    entity_id = f"user-{profile_index:04d}"
    project_id = f"project-{project_index:04d}"
    timestamp = _iso(_BASE_TIME + timedelta(days=index, minutes=rng.randrange(0, 1440)))
    record_id = _stable_id("rec", request.seed, family, index)
    key = f"{family}_key_{index:05d}"
    value = f"{family}_value_{rng.randrange(100000, 999999)}"
    should_retrieve = True
    active = True
    supersedes: str | None = None
    expected_action = "retrieve"
    valid_until: str | None = None

    if family == "user_profile":
        content = f"{entity_id} has preference {key}={value}."
        topic = "user"
        project = None
    elif family == "project_fact":
        content = f"{project_id} uses setting {key}={value}."
        topic = "project"
        project = project_id
    elif family == "code_decision":
        content = f"For {project_id}, decision {key} is {value}."
        topic = "programming"
        project = project_id
    elif family == "contradiction":
        supersedes = _stable_id("old", request.seed, family, index)
        content = f"The current value of {key} for {entity_id} is {value}; older value is obsolete."
        topic = "user"
        project = None
        expected_action = "prefer_newest"
    elif family == "update":
        supersedes = _stable_id("old", request.seed, family, index)
        content = f"Update {project_id}: {key} is now {value}."
        topic = "project"
        project = project_id
        expected_action = "replace"
    elif family == "forget":
        content = f"Forgotten fact {key}={value} for {entity_id}."
        topic = "user"
        project = None
        should_retrieve = False
        active = False
        expected_action = "forget"
        valid_until = timestamp
    elif family == "duplicate":
        content = f"Duplicate candidate for {project_id}: {key}={value}."
        topic = "project"
        project = project_id
        should_retrieve = False
        expected_action = "deduplicate"
    elif family == "temporal":
        valid_until = _iso(_BASE_TIME + timedelta(days=index + 30))
        content = f"Temporal rule {key}={value} is valid for {project_id}."
        topic = "project"
        project = project_id
        expected_action = "respect_validity"
    else:
        raise ValueError(f"Unsupported family: {family}")

    record = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "record_id": record_id,
        "family": family,
        "entity_id": entity_id,
        "project_id": project,
        "content": content,
        "canonical_fact": {"key": key, "value": value},
        "created_at": timestamp,
        "valid_from": timestamp,
        "valid_until": valid_until,
        "supersedes": supersedes,
        "active": active,
        "should_retrieve": should_retrieve,
        "expected_action": expected_action,
        "expected_topic": topic,
        "protected": family in {"code_decision", "temporal"},
        "tags": [family, topic, request.size.value],
    }

    query = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "query_id": _stable_id("qry", request.seed, family, index),
        "family": family,
        "query": f"What is the current value of {key}?",
        "expected_record_ids": [record_id] if should_retrieve else [],
        "forbidden_record_ids": [record_id] if not should_retrieve else [],
        "expected_key": key,
        "expected_value": value if should_retrieve else None,
        "entity_id": entity_id,
        "project_id": project,
        "evaluation": "exact_fact",
    }
    return record, query


def _build_distractor(*, index: int, request: DatasetRequest, rng: random.Random) -> dict[str, Any]:
    timestamp = _iso(_BASE_TIME + timedelta(days=index, seconds=rng.randrange(0, 86400)))
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "record_id": _stable_id("dst", request.seed, "distractor", index),
        "family": "distractor",
        "entity_id": f"noise-user-{index % max(1, request.profile_count):04d}",
        "project_id": None,
        "content": f"Unrelated noise token {rng.randrange(10**8, 10**9)}.",
        "canonical_fact": None,
        "created_at": timestamp,
        "valid_from": timestamp,
        "valid_until": None,
        "supersedes": None,
        "active": True,
        "should_retrieve": False,
        "expected_action": "ignore",
        "expected_topic": "noise",
        "protected": False,
        "tags": ["distractor", request.size.value],
    }


def _validate_generated_records(
    records: Sequence[Mapping[str, Any]],
    queries: Sequence[Mapping[str, Any]],
    request: DatasetRequest | None,
    expected_target_count: int | None,
) -> None:
    ids = [str(item.get("record_id", "")) for item in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate record_id detected.")
    if any(item.get("family") not in FAMILIES for item in records):
        raise ValueError("Unknown record family detected.")
    family_set = {str(item["family"]) for item in records}
    if family_set != set(FAMILIES):
        missing = sorted(set(FAMILIES).difference(family_set))
        raise ValueError("Dataset is missing families: " + ", ".join(missing))
    if expected_target_count is not None:
        actual_target_count = sum(item["family"] != "distractor" for item in records)
        if actual_target_count != expected_target_count:
            raise ValueError("Generated target count does not match size contract.")
    if request is not None and request.include_queries:
        if len(queries) != sum(item["family"] != "distractor" for item in records):
            raise ValueError("Every target memory must have one query.")
    query_ids = [str(item.get("query_id", "")) for item in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Duplicate query_id detected.")
    record_id_set = set(ids)
    for query in queries:
        referenced = list(query.get("expected_record_ids", [])) + list(
            query.get("forbidden_record_ids", [])
        )
        if any(item not in record_id_set for item in referenced):
            raise ValueError("Query references an unknown record_id.")


def _stable_id(prefix: str, seed: int, family: str, index: int) -> str:
    digest = hashlib.sha256(f"{seed}|{family}|{index}".encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{family}-{index:06d}-{digest}"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    text = "".join(canonical_json(row) + "\n" for row in rows)
    return text.encode("utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at line {line_number} in {path.name}.") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL line {line_number} must contain an object.")
        rows.append(payload)
    return rows
