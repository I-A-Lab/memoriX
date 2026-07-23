"""Deterministic project snapshot reconstruction."""

from __future__ import annotations

from memory.cold_site.project_archive.store import (
    ProjectArchiveStore,
)
from memory.data import (
    ProjectArchiveEntry,
    ProjectArchiveEntryType,
    ProjectSnapshot,
    utc_now_iso,
)


class MissingProjectIdentityError(ValueError):
    """Raised when a project snapshot has no identity entry."""


class ProjectArchiveService:
    """Create append-only entries and deterministic snapshots."""

    def __init__(
        self,
        store: ProjectArchiveStore,
    ) -> None:
        self._store = store

    def record_entry(
        self,
        entry: ProjectArchiveEntry,
    ) -> ProjectArchiveEntry:
        return self._store.append_entry(entry)

    def rebuild_snapshot(
        self,
        project_id: str,
        *,
        updated_at: str | None = None,
    ) -> ProjectSnapshot:
        entries = self._store.list_entries(
            project_id=project_id
        )

        if not entries:
            raise ValueError(
                "No project archive entries exist for "
                f"{project_id}."
            )

        identity_entries = tuple(
            entry
            for entry in entries
            if entry.entry_type
            is ProjectArchiveEntryType.IDENTITY
        )

        if not identity_entries:
            raise MissingProjectIdentityError(
                "A project snapshot requires at least "
                "one identity entry."
            )

        latest_identity = identity_entries[-1]
        previous = self._store.latest_snapshot(project_id)

        def values(
            entry_type: ProjectArchiveEntryType,
        ) -> tuple[str, ...]:
            return tuple(
                entry.content
                for entry in entries
                if entry.entry_type is entry_type
            )

        snapshot = ProjectSnapshot(
            project_id=project_id,
            name=latest_identity.title,
            summary=latest_identity.content,
            objectives=values(
                ProjectArchiveEntryType.OBJECTIVE
            ),
            decisions=values(
                ProjectArchiveEntryType.DECISION
            ),
            architecture=values(
                ProjectArchiveEntryType.ARCHITECTURE
            ),
            milestones=values(
                ProjectArchiveEntryType.MILESTONE
            ),
            completed_tasks=values(
                ProjectArchiveEntryType.TASK_COMPLETED
            ),
            remaining_tasks=values(
                ProjectArchiveEntryType.TASK_REMAINING
            ),
            problems=values(
                ProjectArchiveEntryType.PROBLEM
            ),
            solutions=values(
                ProjectArchiveEntryType.SOLUTION
            ),
            latest_changes=values(
                ProjectArchiveEntryType.CHANGE
            ),
            source_entry_ids=tuple(
                entry.entry_id
                for entry in entries
            ),
            version=(
                previous.version + 1
                if previous is not None
                else 1
            ),
            updated_at=updated_at or utc_now_iso(),
        )

        return self._store.append_snapshot(snapshot)
