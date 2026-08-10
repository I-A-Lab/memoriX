from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True, slots=True)
class CampaignManifest:
    campaign_id: str
    profile_name: str
    seeds: List[int]
    total_pairs: int
    created_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "profile_name": self.profile_name,
            "seeds": self.seeds,
            "total_pairs": self.total_pairs,
            "created_by": self.created_by,
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CampaignManifest:
        return cls(
            campaign_id=data["campaign_id"],
            profile_name=data["profile_name"],
            seeds=data["seeds"],
            total_pairs=data["total_pairs"],
            created_by=data.get("created_by", ""),
        )


@dataclass(frozen=True, slots=True)
class RunResult:
    schema_version: int
    run_id: str
    campaign_id: str
    family: str
    mode: str
    seed: int
    pair_index: int
    status: str
    failure_category: str
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    rss_bytes: int = 0
    cpu_percent: float = 0.0
    duration_ms: float = 0.0
    artifacts_path: str = ""
    created_at_utc: str = ""
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "campaign_id": self.campaign_id,
            "family": self.family,
            "mode": self.mode,
            "seed": self.seed,
            "pair_index": self.pair_index,
            "status": self.status,
            "failure_category": self.failure_category,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "rss_bytes": self.rss_bytes,
            "cpu_percent": self.cpu_percent,
            "duration_ms": self.duration_ms,
            "artifacts_path": self.artifacts_path,
            "created_at_utc": self.created_at_utc,
            "dry_run": self.dry_run,
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def fingerprint(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class RunMetrics:
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    rss_bytes: int = 0
    cpu_percent: float = 0.0


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    rss_bytes: int = 0
    cpu_percent: float = 0.0
    disk_bytes: int = 0
    runtime_size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class AggregateMetrics:
    mean_precision: float = 0.0
    mean_recall: float = 0.0
    mean_f1: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    pass_rate: float = 0.0
    total_runs: int = 0
    failed_runs: int = 0


@dataclass(frozen=True, slots=True)
class StatisticalTest:
    test_name: str
    metric: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: float = 0.0


@dataclass(frozen=True, slots=True)
class AggregateReport:
    schema_version: int
    campaign_id: str
    family: str
    suite: str = ""
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    pass_rate: float = 0.0
    median_latency: float = 0.0
    p95_latency: float = 0.0
    max_latency: float = 0.0
    total_runs: int = 0
    failed_runs: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    est_cost: float = 0.0
    avg_rss_mb: float = 0.0
    avg_cpu: float = 0.0
    avg_disk_mb: float = 0.0
    metrics: AggregateMetrics | None = None
    comparisons: Dict[str, Any] = field(default_factory=dict)
    statistical_tests: List[StatisticalTest] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "campaign_id": self.campaign_id,
            "family": self.family,
            "suite": self.suite,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "pass_rate": self.pass_rate,
            "median_latency": self.median_latency,
            "p95_latency": self.p95_latency,
            "max_latency": self.max_latency,
            "total_runs": self.total_runs,
            "failed_runs": self.failed_runs,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "est_cost": self.est_cost,
            "avg_rss_mb": self.avg_rss_mb,
            "avg_cpu": self.avg_cpu,
            "avg_disk_mb": self.avg_disk_mb,
            "statistical_tests": [t.__dict__ for t in self.statistical_tests],
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def make_run_result(
    *,
    campaign_id: str,
    family: str,
    mode: str,
    seed: int,
    pair_index: int,
    status: str = "passed",
    failure_category: str = "PASS",
    precision: float = 0.0,
    recall: float = 0.0,
    f1: float = 0.0,
    latency_ms: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
    rss_bytes: int = 0,
    cpu_percent: float = 0.0,
    duration_ms: float = 0.0,
    dry_run: bool = False,
) -> RunResult:
    import uuid
    from datetime import datetime, timezone

    return RunResult(
        schema_version=1,
        run_id=str(uuid.uuid4()),
        campaign_id=campaign_id,
        family=family,
        mode=mode,
        seed=seed,
        pair_index=pair_index,
        status=status,
        failure_category=failure_category,
        precision=precision,
        recall=recall,
        f1=f1,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=estimated_cost_usd,
        rss_bytes=rss_bytes,
        cpu_percent=cpu_percent,
        duration_ms=duration_ms,
        dry_run=dry_run,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )
