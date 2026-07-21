"""End-to-end smoke scenario for the final memoriX demonstration."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from memory.data import MemoryStoragePaths, ProjectArchiveEntryType
from memory.gateway import MemoriXGateway


@dataclass(frozen=True, slots=True)
class DemoSmokeReport:
    """Result of one isolated end-to-end memory workflow."""

    status: str
    runtime_root: str
    event_id: str
    candidate_id: str
    memory_id: str
    short_term_event_count: int
    cold_event_count: int
    pending_before_validation: int
    validated_candidate_count: int
    retrieved_memory_count: int
    project_archive_entry_count: int
    isolated_runtime: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "runtime_root": self.runtime_root,
            "event_id": self.event_id,
            "candidate_id": self.candidate_id,
            "memory_id": self.memory_id,
            "short_term_event_count": self.short_term_event_count,
            "cold_event_count": self.cold_event_count,
            "pending_before_validation": self.pending_before_validation,
            "validated_candidate_count": self.validated_candidate_count,
            "retrieved_memory_count": self.retrieved_memory_count,
            "project_archive_entry_count": self.project_archive_entry_count,
            "isolated_runtime": self.isolated_runtime,
        }


def run_demo_smoke(
    runtime_root: str | Path | None = None,
) -> DemoSmokeReport:
    """Exercise event, candidate, validation, Titan, and cold archive."""

    temporary = None
    if runtime_root is None:
        temporary = tempfile.TemporaryDirectory(
            prefix="memorix-demo-smoke-"
        )
        runtime = Path(temporary.name).resolve()
    else:
        runtime = Path(runtime_root).expanduser().resolve()

    try:
        paths = MemoryStoragePaths.from_runtime_root(runtime)
        gateway = MemoriXGateway(
            storage_paths=paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_top_k=5,
            titan_min_score=0.0,
        )
        recorded = gateway.record_memory_event(
            content=(
                "QuickTemp converts Celsius, Fahrenheit, and Kelvin "
                "and rounds every result to one decimal place."
            ),
            event_type="demo_project_convention",
            source="memorix_demo_smoke",
            project_id="QuickTemp",
            session_id="part-28-smoke",
            importance=0.9,
            confidence=1.0,
            surprise=0.6,
        )
        candidate = gateway.propose_memory_candidate(
            content=(
                "QuickTemp uses one-decimal temperature conversions "
                "for Celsius, Fahrenheit, and Kelvin."
            ),
            reason="Final end-to-end release smoke test.",
            source_event_ids=(recorded.short_term_event.event_id,),
            importance=0.9,
            confidence=1.0,
            surprise=0.6,
            metadata={"project_id": "QuickTemp"},
        )
        pending = gateway.list_memory_candidates()
        validated = gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="release-smoke",
            validation_reason="Explicit automated acceptance fixture.",
        )
        retrieved = gateway.retrieve_memory(
            "QuickTemp one decimal Celsius Fahrenheit Kelvin",
            top_k=5,
        )
        gateway.record_project_archive_entry(
            project_id="QuickTemp",
            entry_type=ProjectArchiveEntryType.DECISION,
            title="QuickTemp conversion convention",
            content=validated.content,
            source_event_ids=(recorded.short_term_event.event_id,),
            author="release-smoke",
        )
        short_count = len(
            gateway.storage_paths.short_term_events.read_text(
                encoding="utf-8"
            ).splitlines()
        )
        cold_count = len(
            gateway.storage_paths.cold_archive_events.read_text(
                encoding="utf-8"
            ).splitlines()
        )
        validated_count = sum(
            item.status.value == "validated"
            for item in gateway.list_memory_candidates()
        )
        archive_count = len(
            gateway.list_project_archive_entries(project_id="QuickTemp")
        )
        report = DemoSmokeReport(
            status="passed" if retrieved.matches else "failed",
            runtime_root=str(runtime),
            event_id=recorded.short_term_event.event_id,
            candidate_id=candidate.candidate_id,
            memory_id=validated.memory_id,
            short_term_event_count=short_count,
            cold_event_count=cold_count,
            pending_before_validation=len(pending),
            validated_candidate_count=validated_count,
            retrieved_memory_count=len(retrieved.matches),
            project_archive_entry_count=archive_count,
            isolated_runtime=True,
        )
        if report.status != "passed":
            raise RuntimeError("Validated QuickTemp memory was not retrieved.")
        return report
    finally:
        if temporary is not None:
            temporary.cleanup()
