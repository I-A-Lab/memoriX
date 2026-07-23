"""Append-only persistence for explicit project archive data."""

from __future__ import annotations

from pathlib import Path

from memory.data import (
    ProjectArchiveEntry,
    ProjectArchiveEntryType,
    ProjectSnapshot,
    append_json_line,
    read_json_lines,
)


class DuplicateProjectArchiveEntryError(ValueError):
    """Raised when one archive entry identifier already exists."""


class DuplicateProjectSnapshotVersionError(ValueError):
    """Raised when a project snapshot version already exists."""


class ProjectArchiveStore:
    """Persist project entries and derived snapshots as append-only JSONL."""

    def __init__(
        self,
        *,
        entries_path: str | Path,
        snapshots_path: str | Path,
    ) -> None:
        self._entries_path = Path(entries_path)
        self._snapshots_path = Path(snapshots_path)

    @property
    def entries_path(self) -> Path:
        return self._entries_path

    @property
    def snapshots_path(self) -> Path:
        return self._snapshots_path

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: ProjectArchiveEntryType | None = None,
    ) -> tuple[ProjectArchiveEntry, ...]:
        entries = tuple(
            ProjectArchiveEntry.from_dict(payload)
            for payload in read_json_lines(self._entries_path)
        )

        if project_id is not None:
            normalized_project_id = project_id.strip()
            if not normalized_project_id:
                raise ValueError("project_id must not be empty.")
            entries = tuple(
                entry
                for entry in entries
                if entry.project_id == normalized_project_id
            )

        if entry_type is not None:
            normalized_entry_type = ProjectArchiveEntryType(entry_type)
            entries = tuple(
                entry
                for entry in entries
                if entry.entry_type is normalized_entry_type
            )

        return entries

    def get_entry(
        self,
        entry_id: str,
    ) -> ProjectArchiveEntry | None:
        normalized_entry_id = entry_id.strip()
        if not normalized_entry_id:
            raise ValueError("entry_id must not be empty.")

        return next(
            (
                entry
                for entry in self.list_entries()
                if entry.entry_id == normalized_entry_id
            ),
            None,
        )

    def append_entry(
        self,
        entry: ProjectArchiveEntry,
    ) -> ProjectArchiveEntry:
        if self.get_entry(entry.entry_id) is not None:
            raise DuplicateProjectArchiveEntryError(
                "Project archive entry already exists: "
                f"{entry.entry_id}"
            )

        append_json_line(
            self._entries_path,
            entry.to_dict(),
        )
        return entry

    def list_snapshots(
        self,
        *,
        project_id: str | None = None,
    ) -> tuple[ProjectSnapshot, ...]:
        snapshots = tuple(
            ProjectSnapshot.from_dict(payload)
            for payload in read_json_lines(self._snapshots_path)
        )

        if project_id is None:
            return snapshots

        normalized_project_id = project_id.strip()
        if not normalized_project_id:
            raise ValueError("project_id must not be empty.")

        return tuple(
            snapshot
            for snapshot in snapshots
            if snapshot.project_id == normalized_project_id
        )

    def latest_snapshot(
        self,
        project_id: str,
    ) -> ProjectSnapshot | None:
        snapshots = self.list_snapshots(project_id=project_id)
        if not snapshots:
            return None

        return max(
            snapshots,
            key=lambda snapshot: snapshot.version,
        )

    def append_snapshot(
        self,
        snapshot: ProjectSnapshot,
    ) -> ProjectSnapshot:
        existing_versions = {
            item.version
            for item in self.list_snapshots(
                project_id=snapshot.project_id
            )
        }

        if snapshot.version in existing_versions:
            raise DuplicateProjectSnapshotVersionError(
                "Project snapshot version already exists: "
                f"{snapshot.project_id}@{snapshot.version}"
            )

        append_json_line(
            self._snapshots_path,
            snapshot.to_dict(),
        )
        return snapshot
