"""Contracts for read-only memoriX runtime diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


class ProbeStatus(str, Enum):
    """Overall health status returned by a live probe."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProbeCheckStatus(str, Enum):
    """Status of one diagnostic check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ProbeCheck:
    """One immutable read-only diagnostic result."""

    check_id: str
    status: ProbeCheckStatus
    message: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.status.value,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class RuntimeFileObservation:
    """Read-only observation of one expected runtime path."""

    logical_name: str
    path: str
    exists: bool
    is_file: bool
    is_directory: bool
    size_bytes: int | None
    line_count: int | None
    record_count: int | None
    valid_json: bool | None
    valid_jsonl: bool | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LiveProbeReport:
    """Complete read-only diagnostic report."""

    probe_id: str
    runtime_root: str
    status: ProbeStatus
    checks: tuple[ProbeCheck, ...]
    files: tuple[RuntimeFileObservation, ...]
    counters: Mapping[str, int]
    safety: Mapping[str, bool]
    generated_at: str
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "runtime_root": self.runtime_root,
            "status": self.status.value,
            "checks": [
                check.to_dict()
                for check in self.checks
            ],
            "files": [
                observation.to_dict()
                for observation in self.files
            ],
            "counters": dict(self.counters),
            "safety": dict(self.safety),
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
        }
