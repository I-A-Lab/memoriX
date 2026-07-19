"""Read-only runtime-aware policy search for memoriX.

The runtime contributes bounded retention examples only. The search remains
fully dry-run and never writes storage, accesses the cold site, or loads Titan.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory.adaptive.policy_search import (
    MemoryPolicyDataset,
    MemoryPolicyEvaluationCase,
    MemoryPolicySearchConfig,
    MemoryPolicySearchResult,
    default_memory_policy_dataset,
    search_memory_policies,
)
from memory.adaptive.retention_scoring import assess_adaptive_retention
from memory.adaptive.runtime_capacity import validate_external_runtime_root
from memory.adaptive.runtime_retention_scoring import retention_input_from_metadata
from memory.data import MemoryStoragePaths
from memory.data.jsonl_store import read_json_lines


def _latest_records(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        memory_id = str(record.get("memory_id") or "").strip()
        if memory_id:
            latest[memory_id] = record
    return tuple(latest[key] for key in sorted(latest))


@dataclass(frozen=True, slots=True)
class RuntimePolicySearchReport:
    status: str
    runtime_root: str
    simulated: bool
    metadata_records: int
    unique_memories: int
    runtime_case_count: int
    synthetic_case_count: int
    assessment_limit: int
    search_result: MemoryPolicySearchResult
    observation_only: bool = True
    dry_run: bool = True
    policy_applied: bool = False
    runtime_modified: bool = False
    cold_site_accessed: bool = False
    neural_model_loaded: bool = False
    pruning_executed: bool = False
    candidate_validated: bool = False
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["search_result"] = self.search_result.to_dict()
        return payload


def inspect_runtime_policy_search(
    *,
    runtime_root: str | Path,
    max_trials: int = 12,
    seed: int = 23,
    assessment_limit: int = 100,
    simulated_memory_count: int | None = None,
    include_synthetic_cases: bool = True,
    observed_at: str | None = None,
) -> RuntimePolicySearchReport:
    """Search policies against bounded runtime-derived expectations."""
    root = validate_external_runtime_root(runtime_root)
    if assessment_limit < 0:
        raise ValueError("assessment_limit must be non-negative.")
    if simulated_memory_count is not None and simulated_memory_count < 0:
        raise ValueError("simulated_memory_count must be non-negative.")

    now = datetime.fromisoformat(observed_at.replace("Z", "+00:00")) if observed_at else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    records: list[dict[str, Any]] = []
    inputs = []
    simulated = simulated_memory_count is not None
    unique_memories = simulated_memory_count or 0

    if simulated:
        sample_count = min(unique_memories, assessment_limit)
        for index in range(sample_count):
            inputs.append(retention_input_from_metadata({
                "memory_id": f"simulated-{index + 1}",
                "active": True,
                "metadata": {
                    "importance": (index % 5) / 4,
                    "confidence": 0.5 + ((index % 3) / 6),
                    "retrieval_score": (index % 4) / 3,
                    "access_count": index % 20,
                    "surprise": (index % 2) * 0.5,
                    "human_validated": True,
                },
            }, observed_at=now))
    else:
        paths = MemoryStoragePaths.from_runtime_root(root)
        records = read_json_lines(paths.titan_metadata)
        latest = _latest_records(records)
        unique_memories = len(latest)
        replaced_ids = {
            str((record.get("metadata") or {}).get("supersedes_memory_id")).strip()
            for record in latest
            if (record.get("metadata") or {}).get("supersedes_memory_id")
        }
        inputs = [
            retention_input_from_metadata(record, observed_at=now, replaced_memory_ids=replaced_ids)
            for record in latest[:assessment_limit]
        ]

    runtime_cases = []
    for index, source in enumerate(inputs, start=1):
        baseline = assess_adaptive_retention(source, assessment_id=f"runtime-baseline-{index}")
        runtime_cases.append(MemoryPolicyEvaluationCase(
            case_id=f"runtime-{index}-{source.memory_id}",
            retention_input=source,
            expected_retention_action=baseline.recommended_action,
            protected_safety_case=source.protected or source.pinned or not source.human_validated,
            low_value_case=baseline.recommended_action in {"deactivate_candidate", "review_for_soft_pruning", "keep_inactive"},
        ))

    synthetic = default_memory_policy_dataset().cases if include_synthetic_cases else ()
    combined = tuple(synthetic) + tuple(runtime_cases)
    if not combined:
        combined = default_memory_policy_dataset().cases
    dataset = MemoryPolicyDataset(cases=combined, dataset_id="memorix-runtime-policy-dataset-v1")
    result = search_memory_policies(
        dataset=dataset,
        config=MemoryPolicySearchConfig(max_trials=max_trials, seed=seed),
    )
    return RuntimePolicySearchReport(
        status="ok",
        runtime_root=str(root),
        simulated=simulated,
        metadata_records=len(records),
        unique_memories=unique_memories,
        runtime_case_count=len(runtime_cases),
        synthetic_case_count=len(synthetic),
        assessment_limit=assessment_limit,
        search_result=result,
    )
