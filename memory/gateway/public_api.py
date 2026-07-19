"""Public Python API for the complete memoriX memory system.

This gateway is the only supported high-level Python entry point.

Active retrieval is strictly hot-site-only. Durable cold history can only be
queried through the explicit search_cold_site_history() audit operation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from memory.cold_site.long_term_store import (
    ColdEventArchive,
    ColdHistorySearchService,
)
from memory.cold_site.project_archive import (
    ProjectArchiveService,
    ProjectArchiveStore,
)
from memory.consolidation import (
    ConsolidationPolicy,
    ConsolidationRunReport,
    MemoryCandidateService,
    MemoryCandidateStore,
    TitanV2ConsolidationService,
)
from memory.data import (
    CandidateStatus,
    ForgetResult,
    MemoryCandidate,
    MemoryStoragePaths,
    Metadata,
    ProjectArchiveEntry,
    ProjectArchiveEntryType,
    ProjectSnapshot,
    RetrievalResult,
    ShortTermEvent,
    ValidatedMemory,
)
from memory.data.paths import DEFAULT_STORAGE_PATHS
from memory.gateway.event_service import (
    MemoryEventService,
    RecordedMemoryEvent,
)
from memory.gateway.validation_service import (
    MemoryValidationService,
)
from memory.gateway.capacity_control import apply_soft_pruning_plan
from memory.gateway.capacity_operations import CapacityOperations
from memory.adaptive import (
    HotMemoryPruningInput, PressureObservationInput,
    inspect_runtime_capacity, observe_memory_pressure, plan_soft_pruning,
    inspect_runtime_memory_pressure, inspect_runtime_memory_pressure_item,
    inspect_runtime_retention_ranking, inspect_runtime_retention_item,
    inspect_runtime_adaptive_routing,
)
from datetime import datetime, timezone
from memory.hot_site.short_term_memory import (
    ShortTermEventStore,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)
from memory.sync import (
    NightlyConsolidationReport,
    NightlyConsolidationService,
)


class MemoriXGateway:
    """Compose all current Python memory components behind one API."""

    def __init__(
        self,
        *,
        storage_paths: MemoryStoragePaths = (
            DEFAULT_STORAGE_PATHS
        ),
        titan_d_model: int = 256,
        titan_hidden_dim: int = 256,
        titan_max_items: int = 50_000,
        titan_device: str = "cpu",
        titan_top_k: int = 5,
        titan_min_score: float = 0.12,
        consolidation_policy: (
            ConsolidationPolicy | None
        ) = None,
    ) -> None:
        self._paths = storage_paths
        self._titan_max_items = titan_max_items

        self._short_term_store = ShortTermEventStore(
            self._paths.short_term_events
        )
        self._cold_archive = ColdEventArchive(
            self._paths.cold_archive_events
        )
        self._cold_search = ColdHistorySearchService(
            self._cold_archive
        )

        self._project_archive_store = (
            ProjectArchiveStore(
                entries_path=(
                    self._paths.project_archive_entries
                ),
                snapshots_path=(
                    self._paths.project_archive_snapshots
                ),
            )
        )
        self._project_archive_service = (
            ProjectArchiveService(
                self._project_archive_store
            )
        )

        self._candidate_store = MemoryCandidateStore(
            self._paths.memory_candidates
        )
        self._candidate_service = (
            MemoryCandidateService(
                self._candidate_store
            )
        )

        self._hot_site = HotSiteTitanMemory(
            neural_state_path=(
                self._paths.titan_neural_state
            ),
            metadata_path=self._paths.titan_metadata,
            d_model=titan_d_model,
            hidden_dim=titan_hidden_dim,
            max_items=titan_max_items,
            device=titan_device,
            top_k=titan_top_k,
            min_score=titan_min_score,
        )

        self._event_service = MemoryEventService(
            self._short_term_store,
            self._cold_archive,
        )

        self._validation_service = (
            MemoryValidationService(
                self._candidate_store,
                self._hot_site,
                configured_capacity=titan_max_items,
            )
        )

        self._consolidation_service = (
            TitanV2ConsolidationService(
                self._short_term_store,
                self._candidate_store,
                self._candidate_service,
                self._hot_site,
                policy=consolidation_policy,
            )
        )

        self._capacity_operations = CapacityOperations(
            lock_path=self._paths.capacity_lock,
            events_path=self._paths.capacity_events,
            latest_path=self._paths.capacity_latest,
        )

        self._nightly_service = (
            NightlyConsolidationService(
                consolidation_service=(
                    self._consolidation_service
                ),
                short_term_store=(
                    self._short_term_store
                ),
                hot_site=self._hot_site,
                cold_archive_path=(
                    self._paths.cold_archive_events
                ),
                log_path=self._paths.nightly_logs,
            )
        )

    @property
    def storage_paths(self) -> MemoryStoragePaths:
        """Return the configured runtime paths."""

        return self._paths

    def record_event(
        self,
        event: ShortTermEvent,
        *,
        archived_at: str | None = None,
    ) -> RecordedMemoryEvent:
        """Record one event in short-term and cold history."""

        return self._event_service.record_event(
            event,
            archived_at=archived_at,
        )

    def record_memory_event(
        self,
        *,
        content: str,
        event_type: str,
        source: str,
        project_id: str | None = None,
        session_id: str | None = None,
        importance: float = 0.5,
        confidence: float = 1.0,
        surprise: float = 0.0,
        metadata: Metadata | None = None,
        event_id: str | None = None,
        created_at: str | None = None,
        archived_at: str | None = None,
    ) -> RecordedMemoryEvent:
        """Create and persist one short-term event.

        The event is written to short-term storage and directly archived in
        the cold site. It is not validated and is not inserted into Titan.
        """

        arguments: dict[str, Any] = {
            "content": content,
            "event_type": event_type,
            "source": source,
            "project_id": project_id,
            "session_id": session_id,
            "importance": importance,
            "confidence": confidence,
            "surprise": surprise,
            "metadata": dict(metadata or {}),
        }

        if event_id is not None:
            arguments["event_id"] = event_id

        if created_at is not None:
            arguments["created_at"] = created_at

        event = ShortTermEvent(**arguments)

        return self.record_event(
            event,
            archived_at=archived_at,
        )

    def record_project_archive_entry(
        self,
        *,
        project_id: str,
        entry_type: ProjectArchiveEntryType | str,
        title: str,
        content: str,
        source_event_ids: Iterable[str],
        author: str,
        metadata: Metadata | None = None,
        entry_id: str | None = None,
        created_at: str | None = None,
        recorded_at: str | None = None,
    ) -> ProjectArchiveEntry:
        """Append one explicit project archive entry."""

        arguments: dict[str, Any] = {
            "project_id": project_id,
            "entry_type": ProjectArchiveEntryType(
                entry_type
            ),
            "title": title,
            "content": content,
            "source_event_ids": tuple(
                source_event_ids
            ),
            "author": author,
            "metadata": dict(metadata or {}),
        }

        if entry_id is not None:
            arguments["entry_id"] = entry_id

        if created_at is not None:
            arguments["created_at"] = created_at

        if recorded_at is not None:
            arguments["recorded_at"] = recorded_at

        return self._project_archive_service.record_entry(
            ProjectArchiveEntry(**arguments)
        )

    def list_project_archive_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: (
            ProjectArchiveEntryType | str | None
        ) = None,
    ) -> tuple[ProjectArchiveEntry, ...]:
        """List explicit cold project archive entries."""

        normalized_entry_type = (
            ProjectArchiveEntryType(entry_type)
            if entry_type is not None
            else None
        )

        return self._project_archive_store.list_entries(
            project_id=project_id,
            entry_type=normalized_entry_type,
        )

    def rebuild_project_snapshot(
        self,
        project_id: str,
        *,
        updated_at: str | None = None,
    ) -> ProjectSnapshot:
        """Derive and append the next project snapshot."""

        return self._project_archive_service.rebuild_snapshot(
            project_id,
            updated_at=updated_at,
        )

    def get_project_snapshot(
        self,
        project_id: str,
    ) -> ProjectSnapshot | None:
        """Return the latest snapshot for one project."""

        return self._project_archive_store.latest_snapshot(
            project_id
        )

    def retrieve_memory(
        self,
        query: str,
        *,
        role: str | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Retrieve active validated memory from Titan only.

        This method never reads the cold archive and never performs automatic
        rehydration.
        """

        return self._hot_site.retrieve(
            query,
            role=role,
            top_k=top_k,
        )

    def search_cold_site_history(
        self,
        query: str,
        *,
        limit: int = 10,
    ) -> RetrievalResult:
        """Explicitly search raw durable event history for audit purposes."""

        return self._cold_search.search(
            query,
            limit=limit,
        )

    def propose_memory_candidate(
        self,
        *,
        content: str,
        reason: str,
        source_event_ids: Iterable[str],
        importance: float = 0.5,
        confidence: float = 0.5,
        surprise: float = 0.0,
        target_memory_id: str | None = None,
        metadata: Metadata | None = None,
    ) -> MemoryCandidate:
        """Create one pending candidate without validating it."""

        return self._candidate_service.propose(
            content=content,
            reason=reason,
            source_event_ids=source_event_ids,
            importance=importance,
            confidence=confidence,
            surprise=surprise,
            target_memory_id=target_memory_id,
            metadata=metadata,
        )

    def list_memory_candidates(
        self,
        *,
        status: CandidateStatus | None = None,
    ) -> tuple[MemoryCandidate, ...]:
        """List candidates, optionally filtered by status."""

        return self._candidate_store.list_candidates(
            status=status
        )

    def validate_memory_candidate(
        self,
        candidate_id: str,
        *,
        validated_by: str,
        validation_reason: str,
        final_content: str | None = None,
    ) -> ValidatedMemory:
        """Human-validate a candidate into the Titan hot site only."""

        return self._validation_service.validate(
            candidate_id,
            validated_by=validated_by,
            validation_reason=validation_reason,
            final_content=final_content,
        )

    def reject_memory_candidate(
        self,
        candidate_id: str,
        *,
        rejected_by: str,
        rejection_reason: str,
    ) -> MemoryCandidate:
        """Reject a candidate without writing to Titan."""

        return self._validation_service.reject(
            candidate_id,
            rejected_by=rejected_by,
            rejection_reason=rejection_reason,
        )

    def forget_memory(
        self,
        memory_id: str,
        *,
        validated_by: str,
        reason: str,
    ) -> ForgetResult:
        """Soft-forget one active memory in Titan only."""

        return self._hot_site.soft_forget(
            memory_id,
            validated_by=validated_by,
            reason=reason,
        )

    def run_consolidation(
        self,
        *,
        mode: str = "manual",
    ) -> ConsolidationRunReport:
        """Run Titan V2 candidate creation without automatic validation."""

        return self._consolidation_service.run(
            mode=mode
        )

    def run_nightly_consolidation(
        self,
        *,
        clear_short_term_after_success: bool = True,
    ) -> NightlyConsolidationReport:
        """Run protected nightly consolidation and hot-site replay."""

        return self._nightly_service.run(
            clear_short_term_after_success=(
                clear_short_term_after_success
            )
        )


    def capacity_status(self, *, simulate_active_items: int | None = None) -> dict[str, Any]:
        snapshot = inspect_runtime_capacity(
            runtime_root=self._paths.runtime_root,
            configured_capacity=self._titan_max_items,
            simulated_active_items=simulate_active_items,
        )
        payload = snapshot.to_dict()
        if simulate_active_items is None:
            self._capacity_operations.record("capacity_checked", payload)
        return payload

    def capacity_plan(self) -> dict[str, Any]:
        memories = self._hot_site.list_memories(active_only=False)
        active_count = sum(memory.active for memory in memories)
        pressure = observe_memory_pressure(PressureObservationInput(
            scope_id="hot_site", used_items=active_count, capacity=self._titan_max_items
        ))
        now = datetime.now(timezone.utc)
        inputs = []
        for memory in memories:
            metadata = dict(memory.metadata)
            try:
                created = datetime.fromisoformat(memory.created_at.replace("Z", "+00:00"))
                age_days = max(0.0, (now - created).total_seconds() / 86400.0)
            except ValueError:
                age_days = 0.0
            inputs.append(HotMemoryPruningInput(
                memory_id=memory.memory_id, block_id="hot_site",
                importance=float(metadata.get("importance", 0.5)),
                access_count=int(metadata.get("access_count", 0)),
                age_days=age_days, retrieval_score=float(metadata.get("retrieval_score", 0.0)),
                active=memory.active, pinned=bool(metadata.get("pinned", False)),
                human_validated=True, metadata=metadata,
            ))
        plan = plan_soft_pruning(scope_id="hot_site", memories=inputs, pressure=pressure)
        payload = plan.to_dict()
        self._capacity_operations.record("pruning_planned", payload)
        return payload

    def capacity_prune(self, *, applied_by: str, reason: str, max_deactivations: int | None = None) -> dict[str, Any]:
        with self._capacity_operations.mutation_lock("capacity_prune"):
            plan_payload = self.capacity_plan()
            from memory.adaptive.contracts import SoftPruningAction, SoftPruningPlan, SoftPruningRecommendation
            recommendations = tuple(SoftPruningRecommendation(
                memory_id=item["memory_id"], block_id=item["block_id"],
                action=SoftPruningAction(item["action"]), retention_score=float(item["retention_score"]),
                pressure=float(item["pressure"]), protected=bool(item["protected"]),
                protection_reasons=tuple(item["protection_reasons"]), scoring_components=dict(item["scoring_components"]),
                explanation=tuple(item["explanation"]),
            ) for item in plan_payload["recommendations"])
            plan = SoftPruningPlan(
                plan_id=plan_payload["plan_id"], scope_id=plan_payload["scope_id"],
                pressure_observation_id=plan_payload["pressure_observation_id"],
                pressure=float(plan_payload["pressure"]), recommendations=recommendations,
                created_at=plan_payload["created_at"],
            )
            report = apply_soft_pruning_plan(plan, self._hot_site, applied_by=applied_by, reason=reason, max_deactivations=max_deactivations)
            payload = report.to_dict()
            self._capacity_operations.record("pruning_completed", payload)
            return payload

    def memory_pressure_status(
        self,
        *,
        simulate_count: int | None = None,
        assessment_limit: int = 100,
    ) -> dict[str, Any]:
        """Inspect persisted hot-site pressure without loading Titan."""

        return inspect_runtime_memory_pressure(
            runtime_root=self._paths.runtime_root,
            assessment_limit=assessment_limit,
            simulated_memory_count=simulate_count,
        ).to_dict()

    def memory_pressure_inspect(
        self,
        memory_id: str,
    ) -> dict[str, Any] | None:
        """Inspect one persisted hot-site memory by identifier."""

        assessment = inspect_runtime_memory_pressure_item(
            runtime_root=self._paths.runtime_root,
            memory_id=memory_id,
        )
        return assessment.to_dict() if assessment is not None else None

    def retention_ranking_status(
        self,
        *,
        simulate_count: int | None = None,
        assessment_limit: int = 100,
    ) -> dict[str, Any]:
        """Rank persisted hot memories without mutation."""

        return inspect_runtime_retention_ranking(
            runtime_root=self._paths.runtime_root,
            assessment_limit=assessment_limit,
            simulated_memory_count=simulate_count,
        ).to_dict()

    def retention_ranking_inspect(
        self,
        memory_id: str,
    ) -> dict[str, Any] | None:
        """Inspect one persisted adaptive-retention assessment."""

        assessment = inspect_runtime_retention_item(
            runtime_root=self._paths.runtime_root,
            memory_id=memory_id,
        )
        return assessment.to_dict() if assessment is not None else None

    def adaptive_routing_plan(
        self,
        *,
        target_id: str,
        retention_score: float = 0.5,
        importance: float = 0.5,
        confidence: float = 0.5,
        surprise: float = 0.0,
        protected: bool = False,
        pinned: bool = False,
        human_validated: bool = True,
        required_slots: int = 1,
        configured_capacity: int = 50_000,
        assessment_limit: int = 100,
        simulate_memory_count: int | None = None,
    ) -> dict[str, Any]:
        """Build one read-only adaptive-routing plan."""

        return inspect_runtime_adaptive_routing(
            runtime_root=self._paths.runtime_root,
            target_id=target_id,
            retention_score=retention_score,
            importance=importance,
            confidence=confidence,
            surprise=surprise,
            protected=protected,
            pinned=pinned,
            human_validated=human_validated,
            required_slots=required_slots,
            configured_capacity=configured_capacity,
            assessment_limit=assessment_limit,
            simulated_memory_count=simulate_memory_count,
        ).to_dict()

    def memory_status(self) -> dict[str, Any]:
        """Return a non-mutating status summary of the Python memory."""

        candidates = (
            self._candidate_store.list_candidates()
        )
        all_hot_memories = (
            self._hot_site.list_memories()
        )
        active_hot_memories = tuple(
            memory
            for memory in all_hot_memories
            if memory.active
        )

        candidate_counts = {
            status.value: sum(
                candidate.status is status
                for candidate in candidates
            )
            for status in CandidateStatus
        }

        return {
            "architecture": "memorix_hot_cold",
            "retrieval_contract": (
                "hot_site_only_no_cold_fallback"
            ),
            "cold_site_contract": (
                "explicit_audit_history_only"
            ),
            "automatic_rehydration": False,
            "short_term_events": len(
                self._short_term_store.list_events()
            ),
            "cold_archive_events": len(
                self._cold_archive.list_events()
            ),
            "project_archive_entries": len(
                self._project_archive_store.list_entries()
            ),
            "project_archive_snapshots": len(
                self._project_archive_store.list_snapshots()
            ),
            "candidates": candidate_counts,
            "hot_memories_total": len(
                all_hot_memories
            ),
            "hot_memories_active": len(
                active_hot_memories
            ),
            "titan": self._hot_site.stats(),
            "paths": {
                "runtime_root": str(
                    self._paths.runtime_root
                ),
                "short_term_events": str(
                    self._paths.short_term_events
                ),
                "cold_archive_events": str(
                    self._paths.cold_archive_events
                ),
                "memory_candidates": str(
                    self._paths.memory_candidates
                ),
                "titan_neural_state": str(
                    self._paths.titan_neural_state
                ),
                "titan_metadata": str(
                    self._paths.titan_metadata
                ),
                "nightly_logs": str(
                    self._paths.nightly_logs
                ),
                "project_archive_entries": str(
                    self._paths.project_archive_entries
                ),
                "project_archive_snapshots": str(
                    self._paths.project_archive_snapshots
                ),
            },
        }


_DEFAULT_GATEWAY: MemoriXGateway | None = None


def get_default_gateway() -> MemoriXGateway:
    """Return the lazily created default gateway."""

    global _DEFAULT_GATEWAY

    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = MemoriXGateway()

    return _DEFAULT_GATEWAY


def reset_default_gateway() -> None:
    """Clear the process-local default gateway reference.

    This helper does not delete any stored data. It is mainly useful for tests
    and controlled runtime reconfiguration.
    """

    global _DEFAULT_GATEWAY
    _DEFAULT_GATEWAY = None


def record_memory_event(
    *,
    content: str,
    event_type: str,
    source: str,
    project_id: str | None = None,
    session_id: str | None = None,
    importance: float = 0.5,
    confidence: float = 1.0,
    surprise: float = 0.0,
    metadata: Metadata | None = None,
) -> RecordedMemoryEvent:
    """Record an event through the default gateway."""

    return get_default_gateway().record_memory_event(
        content=content,
        event_type=event_type,
        source=source,
        project_id=project_id,
        session_id=session_id,
        importance=importance,
        confidence=confidence,
        surprise=surprise,
        metadata=metadata,
    )


def retrieve_memory(
    query: str,
    *,
    role: str | None = None,
    top_k: int | None = None,
) -> RetrievalResult:
    """Retrieve active memory from the default Titan hot site only."""

    return get_default_gateway().retrieve_memory(
        query,
        role=role,
        top_k=top_k,
    )


def search_cold_site_history(
    query: str,
    *,
    limit: int = 10,
) -> RetrievalResult:
    """Explicitly search durable cold history."""

    return get_default_gateway().search_cold_site_history(
        query,
        limit=limit,
    )
