"""Nightly consolidation and active-memory replay for memoriX.

The nightly path is restricted to:

short-term events
-> Titan V2 candidate creation
-> active hot-site replay

The cold site is snapshotted before and after the run and must remain exactly
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

from memory.consolidation import (
    ConsolidationRunReport,
    TitanV2ConsolidationService,
)
from memory.data import JSONValue, utc_now_iso
from memory.data.jsonl_store import append_json_line
from memory.hot_site.short_term_memory import (
    ShortTermEventStore,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)
from memory.hot_site.titan_active_memory.elastic_capacity import (
    NightlyCapacityMaintenanceResult,
    run_nightly_capacity_maintenance,
)

if TYPE_CHECKING:
    from memory.gateway.capacity_operations import (
        CapacityOperations,
    )


NIGHTLY_SCOPE = "short_term_to_hot_site_only"
COLD_SITE_CONTRACT = (
    "direct_archive_only_excluded_from_nightly_consolidation"
)


class ColdSiteModifiedError(RuntimeError):
    """Raised when a nightly run modifies durable cold history."""


@dataclass(frozen=True, slots=True)
class ColdSiteSnapshot:
    """Immutable fingerprint of the cold archive."""

    exists: bool
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the snapshot."""

        return {
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class NightlyConsolidationReport:
    """Structured result of one successful nightly run."""

    started_at: str
    completed_at: str
    nightly_scope: str
    cold_site_contract: str
    cold_site_modified: bool
    automatic_candidate_validation: bool
    consolidation: ConsolidationRunReport
    active_memories_replayed: int
    short_term_events_cleared: int
    cold_before: ColdSiteSnapshot
    cold_after: ColdSiteSnapshot
    capacity_maintenance: (
        NightlyCapacityMaintenanceResult | None
    ) = None

    def to_dict(self) -> dict[str, JSONValue]:
        """Serialize the nightly report."""

        return {
            "status": "completed",
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "nightly_scope": self.nightly_scope,
            "cold_site_contract": (
                self.cold_site_contract
            ),
            "cold_site_modified": (
                self.cold_site_modified
            ),
            "automatic_candidate_validation": (
                self.automatic_candidate_validation
            ),
            "active_memories_replayed": (
                self.active_memories_replayed
            ),
            "short_term_events_cleared": (
                self.short_term_events_cleared
            ),
            "consolidation": (
                self.consolidation.to_dict()
            ),
            "cold_before": self.cold_before.to_dict(),
            "cold_after": self.cold_after.to_dict(),
            "capacity_maintenance": (
                self.capacity_maintenance.to_dict()
                if self.capacity_maintenance is not None
                else None
            ),
        }


def snapshot_file(path: str | Path) -> ColdSiteSnapshot:
    """Return a deterministic fingerprint of one file."""

    target = Path(path)

    if not target.exists():
        return ColdSiteSnapshot(
            exists=False,
            size_bytes=0,
            sha256=hashlib.sha256(b"").hexdigest(),
        )

    payload = target.read_bytes()

    return ColdSiteSnapshot(
        exists=True,
        size_bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
    )


class NightlyConsolidationService:
    """Run consolidation and replay while protecting cold history."""

    def __init__(
        self,
        *,
        consolidation_service: (
            TitanV2ConsolidationService
        ),
        short_term_store: ShortTermEventStore,
        hot_site: HotSiteTitanMemory,
        cold_archive_path: str | Path,
        log_path: str | Path,
        capacity_operations: (
            CapacityOperations | None
        ) = None,
    ) -> None:
        self._consolidation_service = (
            consolidation_service
        )
        self._short_term_store = short_term_store
        self._hot_site = hot_site
        self._cold_archive_path = Path(
            cold_archive_path
        )
        self._log_path = Path(log_path)
        self._capacity_operations = capacity_operations

    def run(
        self,
        *,
        clear_short_term_after_success: bool = True,
    ) -> NightlyConsolidationReport:
        """Execute one protected nightly consolidation run."""

        if not isinstance(
            clear_short_term_after_success,
            bool,
        ):
            raise TypeError(
                "clear_short_term_after_success "
                "must be a boolean."
            )

        started_at = utc_now_iso()
        cold_before = snapshot_file(
            self._cold_archive_path
        )

        consolidation_report = (
            self._consolidation_service.run(
                mode="nightly"
            )
        )

        replayed = (
            self._hot_site.replay_active_memories(
                replayed_by="memorix_nightly",
                replay_reason=(
                    "Nightly replay of active validated "
                    "hot-site memories."
                ),
            )
        )

        capacity_maintenance = None

        if self._capacity_operations is not None:
            capacity_maintenance = (
                run_nightly_capacity_maintenance(
                    self._hot_site,
                    capacity_operations=(
                        self._capacity_operations
                    ),
                    run_reference=started_at,
                    cold_archive_path=(
                        self._cold_archive_path
                    ),
                    log_path=self._log_path,
                )
            )

        cold_after_processing = snapshot_file(
            self._cold_archive_path
        )

        if cold_after_processing != cold_before:
            raise ColdSiteModifiedError(
                "The cold archive changed during nightly "
                "consolidation."
            )

        cleared = 0

        if clear_short_term_after_success:
            cleared = self._short_term_store.clear()

        cold_after = snapshot_file(
            self._cold_archive_path
        )

        if cold_after != cold_before:
            raise ColdSiteModifiedError(
                "The cold archive changed after short-term "
                "cleanup."
            )

        report = NightlyConsolidationReport(
            started_at=started_at,
            completed_at=utc_now_iso(),
            nightly_scope=NIGHTLY_SCOPE,
            cold_site_contract=COLD_SITE_CONTRACT,
            cold_site_modified=False,
            automatic_candidate_validation=False,
            consolidation=consolidation_report,
            active_memories_replayed=replayed,
            short_term_events_cleared=cleared,
            cold_before=cold_before,
            cold_after=cold_after,
            capacity_maintenance=capacity_maintenance,
        )

        append_json_line(
            self._log_path,
            report.to_dict(),
        )

        return report
