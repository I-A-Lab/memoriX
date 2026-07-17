"""Read-only adaptive-retention ranking from persisted Titan metadata."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from memory.adaptive.retention_scoring import (
    HotSiteRetentionRanking,
    RetentionScoreAssessment,
    RetentionScoringInput,
    assess_adaptive_retention,
    rank_hot_site_memories,
)
from memory.adaptive.runtime_capacity import validate_external_runtime_root
from memory.data import MemoryStoragePaths
from memory.data.jsonl_store import read_json_lines


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _latest(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
        if memory_id:
            latest[memory_id] = record
    return latest


def retention_input_from_metadata(
    record: Mapping[str, Any],
    *,
    observed_at: datetime,
    replaced_memory_ids: set[str] | None = None,
) -> RetentionScoringInput:
    memory_id = str(record.get("memory_id") or record.get("id") or "").strip()
    if not memory_id:
        raise ValueError("Titan metadata record has no memory_id.")

    metadata = dict(record.get("metadata") or {})
    created = _timestamp(
        metadata.get("created_at")
        or metadata.get("validated_at")
        or record.get("stored_at")
    )
    age_days = (
        0.0
        if created is None
        else max(0.0, (observed_at - created).total_seconds() / 86400.0)
    )

    return RetentionScoringInput(
        memory_id=memory_id,
        age_days=age_days,
        access_count=int(
            max(
                0.0,
                _finite(
                    metadata.get("access_count", record.get("access_count", 0))
                ),
            )
        ),
        importance=_finite(
            metadata.get("importance", record.get("importance", 0.5)),
            0.5,
        ),
        retrieval_score=_finite(
            metadata.get(
                "retrieval_score",
                record.get("retrieval_score", 0.5),
            ),
            0.5,
        ),
        confidence=_finite(
            metadata.get("confidence", record.get("confidence", 0.5)),
            0.5,
        ),
        momentum=_finite(
            metadata.get("momentum", record.get("momentum", 0.0))
        ),
        surprise=_finite(
            metadata.get("surprise", record.get("surprise", 0.0))
        ),
        active=bool(record.get("active", metadata.get("active", True))),
        replaced=(
            memory_id in (replaced_memory_ids or set())
            or bool(metadata.get("replaced", False))
        ),
        protected=bool(metadata.get("protected", False)),
        pinned=bool(metadata.get("pinned", False)),
        human_validated=bool(metadata.get("human_validated", True)),
        metadata=metadata,
        observed_at=observed_at.isoformat(),
    )


@dataclass(frozen=True, slots=True)
class RuntimeRetentionRankingReport:
    status: str
    runtime_root: str
    simulated: bool
    metadata_records: int
    unique_memories: int
    assessment_limit: int
    assessments_truncated: bool
    ranking: HotSiteRetentionRanking
    observation_only: bool = True
    dry_run: bool = True
    applied: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ranking"] = self.ranking.to_dict()
        return payload


def inspect_runtime_retention_ranking(
    *,
    runtime_root: str | Path,
    assessment_limit: int = 100,
    simulated_memory_count: int | None = None,
    observed_at: str | None = None,
) -> RuntimeRetentionRankingReport:
    root = validate_external_runtime_root(runtime_root)
    if assessment_limit < 0:
        raise ValueError("assessment_limit must be non-negative.")

    now = _timestamp(observed_at) if observed_at else datetime.now(timezone.utc)
    if now is None:
        raise ValueError("observed_at must be an ISO-8601 timestamp.")

    if simulated_memory_count is not None:
        if simulated_memory_count < 0:
            raise ValueError("simulated_memory_count must be non-negative.")

        sample = RetentionScoringInput(
            memory_id="simulated_low_retention",
            age_days=730,
            access_count=0,
            importance=0.0,
            retrieval_score=0.0,
            confidence=0.0,
            momentum=0.0,
            surprise=0.0,
            replaced=True,
            observed_at=now.isoformat(),
        )
        assessment = assess_adaptive_retention(
            sample,
            assessment_id="simulated_retention",
            rank=1,
        )
        action_counts = {
            "keep_protected": 0,
            "keep_inactive": 0,
            "keep": 0,
            "watch": 0,
            "review_for_soft_pruning": 0,
            "deactivate_candidate": 0,
        }
        if simulated_memory_count:
            action_counts[assessment.recommended_action] = simulated_memory_count

        ranking = HotSiteRetentionRanking(
            ranking_id="simulated_retention_ranking",
            observed_at=now.isoformat(),
            memory_count=simulated_memory_count,
            mean_retention=(
                assessment.retention_score if simulated_memory_count else 0.0
            ),
            maximum_retention=(
                assessment.retention_score if simulated_memory_count else 0.0
            ),
            minimum_retention=(
                assessment.retention_score if simulated_memory_count else 0.0
            ),
            protected_count=0,
            action_counts=action_counts,
            assessments=(
                (assessment,)
                if simulated_memory_count and assessment_limit
                else ()
            ),
        )
        return RuntimeRetentionRankingReport(
            status="ok",
            runtime_root=str(root),
            simulated=True,
            metadata_records=0,
            unique_memories=simulated_memory_count,
            assessment_limit=assessment_limit,
            assessments_truncated=(
                simulated_memory_count > len(ranking.assessments)
            ),
            ranking=ranking,
        )

    paths = MemoryStoragePaths.from_runtime_root(root)
    records = read_json_lines(paths.titan_metadata)
    latest = _latest(records)
    replaced_ids = {
        str(
            (record.get("metadata") or {}).get("supersedes_memory_id")
        ).strip()
        for record in latest.values()
        if (record.get("metadata") or {}).get("supersedes_memory_id")
    }
    inputs = tuple(
        retention_input_from_metadata(
            record,
            observed_at=now,
            replaced_memory_ids=replaced_ids,
        )
        for _, record in sorted(latest.items())
    )

    full = rank_hot_site_memories(
        inputs,
        observed_at=now.isoformat(),
        ranking_id="runtime_retention_ranking",
    )
    limited = HotSiteRetentionRanking(
        ranking_id=full.ranking_id,
        observed_at=full.observed_at,
        memory_count=full.memory_count,
        mean_retention=full.mean_retention,
        maximum_retention=full.maximum_retention,
        minimum_retention=full.minimum_retention,
        protected_count=full.protected_count,
        action_counts=full.action_counts,
        assessments=full.assessments[:assessment_limit],
    )
    return RuntimeRetentionRankingReport(
        status="ok",
        runtime_root=str(root),
        simulated=False,
        metadata_records=len(records),
        unique_memories=len(latest),
        assessment_limit=assessment_limit,
        assessments_truncated=(
            len(full.assessments) > len(limited.assessments)
        ),
        ranking=limited,
    )


def inspect_runtime_retention_item(
    *,
    runtime_root: str | Path,
    memory_id: str,
    observed_at: str | None = None,
) -> RetentionScoreAssessment | None:
    target = memory_id.strip()
    if not target:
        raise ValueError("memory_id must be non-empty.")

    report = inspect_runtime_retention_ranking(
        runtime_root=runtime_root,
        assessment_limit=1_000_000,
        observed_at=observed_at,
    )
    for assessment in report.ranking.assessments:
        if assessment.memory_id == target:
            return assessment
    return None
