"""Versioned run manifests for the global memoriX benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from memory.benchmark.global_contracts import (
    BENCHMARK_ID,
    SCHEMA_VERSION,
    BenchmarkMode,
    BenchmarkSize,
    BenchmarkSuite,
    load_benchmark_contracts,
)

_RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,64}$")


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Stable user-controlled inputs for one benchmark execution."""

    mode: BenchmarkMode
    suite: BenchmarkSuite
    size: BenchmarkSize
    seed: int
    task_id: str
    dataset_id: str
    prompt_version: str
    model_id: str
    model_parameters: Mapping[str, Any]
    tool_budget: int
    turn_budget: int
    timeout_seconds: int
    evaluator_version: str
    paired_run_group_id: str

    def validate(self) -> None:
        for name in (
            "task_id",
            "dataset_id",
            "prompt_version",
            "model_id",
            "evaluator_version",
            "paired_run_group_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.seed < 0:
            raise ValueError("seed must be non-negative.")
        if self.tool_budget < 0:
            raise ValueError("tool_budget must be non-negative.")
        if self.turn_budget <= 0:
            raise ValueError("turn_budget must be positive.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if not isinstance(self.model_parameters, Mapping):
            raise ValueError("model_parameters must be a mapping.")


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    """Reproducibility metadata captured before a run starts."""

    captured_at_utc: str
    platform: str
    platform_release: str
    architecture: str
    machine: str
    processor: str
    python_version: str
    python_executable: str
    bun_version: str
    git_commit: str
    git_dirty: bool
    repository_root: str
    hardware_id: str

    def validate(self) -> None:
        _parse_utc(self.captured_at_utc, "captured_at_utc")
        if not _GIT_COMMIT_PATTERN.fullmatch(self.git_commit):
            raise ValueError("git_commit must be a hexadecimal Git commit ID.")
        if not self.python_version:
            raise ValueError("python_version is required.")
        if not self.repository_root:
            raise ValueError("repository_root is required.")
        if not _SHA256_PATTERN.fullmatch(self.hardware_id):
            raise ValueError("hardware_id must be a SHA-256 hexadecimal digest.")


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Immutable manifest written before a benchmark process is launched."""

    schema_version: int
    benchmark_id: str
    run_id: str
    created_at_utc: str
    request: RunRequest
    environment: EnvironmentSnapshot
    runtime_root: str | None
    configuration_fingerprint: str
    status: str = "planned"

    def validate(self, *, repository_root: Path | None = None) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version={self.schema_version}; "
                f"expected {SCHEMA_VERSION}."
            )
        if self.benchmark_id != BENCHMARK_ID:
            raise ValueError(f"benchmark_id must be {BENCHMARK_ID!r}.")
        if not _RUN_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError("run_id contains unsupported characters or is too short.")
        _parse_utc(self.created_at_utc, "created_at_utc")
        if self.status != "planned":
            raise ValueError("A newly created manifest must have status='planned'.")
        self.request.validate()
        self.environment.validate()

        contracts = load_benchmark_contracts(
            Path(self.environment.repository_root)
            / "benchmarks"
            / "memorix_vs_no_memory"
            / "configs"
        )
        mode_contract = next(
            item for item in contracts.modes if item.mode is self.request.mode
        )
        if self.request.size not in {item.size for item in contracts.sizes}:
            raise ValueError("Unknown benchmark size.")

        if self.request.mode is BenchmarkMode.NO_MEMORY:
            if self.runtime_root is not None:
                raise ValueError("no_memory must not define a memoriX runtime_root.")
        if mode_contract.runtime_creation_allowed and self.runtime_root is None:
            raise ValueError(
                f"{self.request.mode.value} requires an isolated runtime_root."
            )

        root = repository_root
        if root is None:
            root = Path(self.environment.repository_root)
        root = root.resolve()
        if self.runtime_root is not None:
            runtime = Path(self.runtime_root).resolve()
            if _is_within(runtime, root):
                raise ValueError("runtime_root must be outside the repository.")

        expected = configuration_fingerprint(
            self.request,
            self.environment.git_commit,
        )
        if self.configuration_fingerprint != expected:
            raise ValueError("configuration_fingerprint does not match the request.")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["request"]["mode"] = self.request.mode.value
        payload["request"]["suite"] = self.request.suite.value
        payload["request"]["size"] = self.request.size.value
        return payload


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def configuration_fingerprint(request: RunRequest, git_commit: str) -> str:
    request.validate()
    payload = asdict(request)
    payload["mode"] = request.mode.value
    payload["suite"] = request.suite.value
    payload["size"] = request.size.value
    payload["git_commit"] = git_commit
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def generate_run_id(request: RunRequest, *, created_at_utc: str) -> str:
    timestamp = _parse_utc(created_at_utc, "created_at_utc").strftime("%Y%m%dt%H%M%Sz")
    short_hash = hashlib.sha256(
        canonical_json(
            {
                "mode": request.mode.value,
                "suite": request.suite.value,
                "size": request.size.value,
                "seed": request.seed,
                "task_id": request.task_id,
                "dataset_id": request.dataset_id,
                "paired_run_group_id": request.paired_run_group_id,
                "created_at_utc": created_at_utc,
            }
        ).encode("utf-8")
    ).hexdigest()[:12]
    return (
        f"{request.suite.value}-{request.mode.value}-{request.size.value}-"
        f"s{request.seed}-{timestamp}-{short_hash}"
    )


def capture_environment(repository_root: Path) -> EnvironmentSnapshot:
    root = repository_root.resolve()
    git_commit = _run_text(["git", "rev-parse", "HEAD"], cwd=root)
    git_status = _run_text(["git", "status", "--porcelain"], cwd=root, allow_empty=True)
    bun_version = _run_text(["bun", "--version"], cwd=root)
    hardware_payload = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "machine": platform.node(),
        "processor": platform.processor(),
    }
    hardware_id = hashlib.sha256(
        canonical_json(hardware_payload).encode("utf-8")
    ).hexdigest()
    snapshot = EnvironmentSnapshot(
        captured_at_utc=utc_now(),
        platform=platform.system(),
        platform_release=platform.release(),
        architecture=platform.architecture()[0],
        machine=platform.node(),
        processor=platform.processor(),
        python_version=platform.python_version(),
        python_executable=sys.executable,
        bun_version=bun_version,
        git_commit=git_commit,
        git_dirty=bool(git_status.strip()),
        repository_root=str(root),
        hardware_id=hardware_id,
    )
    snapshot.validate()
    return snapshot


def build_manifest(
    request: RunRequest,
    environment: EnvironmentSnapshot,
    *,
    runtime_root: Path | None,
    created_at_utc: str | None = None,
) -> RunManifest:
    request.validate()
    created = created_at_utc or utc_now()
    manifest = RunManifest(
        schema_version=SCHEMA_VERSION,
        benchmark_id=BENCHMARK_ID,
        run_id=generate_run_id(request, created_at_utc=created),
        created_at_utc=created,
        request=request,
        environment=environment,
        runtime_root=None if runtime_root is None else str(runtime_root.resolve()),
        configuration_fingerprint=configuration_fingerprint(
            request,
            environment.git_commit,
        ),
    )
    manifest.validate(repository_root=Path(environment.repository_root))
    return manifest


def load_manifest(path: Path) -> RunManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    request_payload = dict(payload["request"])
    request_payload["mode"] = BenchmarkMode(request_payload["mode"])
    request_payload["suite"] = BenchmarkSuite(request_payload["suite"])
    request_payload["size"] = BenchmarkSize(request_payload["size"])
    request = RunRequest(**request_payload)
    environment = EnvironmentSnapshot(**payload["environment"])
    manifest = RunManifest(
        schema_version=int(payload["schema_version"]),
        benchmark_id=str(payload["benchmark_id"]),
        run_id=str(payload["run_id"]),
        created_at_utc=str(payload["created_at_utc"]),
        request=request,
        environment=environment,
        runtime_root=payload.get("runtime_root"),
        configuration_fingerprint=str(payload["configuration_fingerprint"]),
        status=str(payload.get("status", "planned")),
    )
    manifest.validate(repository_root=Path(environment.repository_root))
    return manifest


def write_manifest_atomic(path: Path, manifest: RunManifest) -> None:
    manifest.validate(repository_root=Path(manifest.environment.repository_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing manifest: {path}")
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _run_text(
    command: list[str],
    *,
    cwd: Path,
    allow_empty: bool = False,
) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stderr.strip()}"
        )
    value = completed.stdout.strip()
    if not value and not allow_empty:
        raise RuntimeError(f"Command returned no output: {' '.join(command)}")
    return value


def _parse_utc(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field_name} must be an ISO-8601 UTC timestamp ending in Z.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO-8601 timestamp.") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field_name} must use UTC.")
    return parsed


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
