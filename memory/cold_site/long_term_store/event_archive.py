"""Durable cold-site archive for raw short-term events."""

from __future__ import annotations

from pathlib import Path

from memory.data import ArchivedEvent, ShortTermEvent
from memory.data.jsonl_store import (
    append_json_line,
    read_json_lines,
)
from memory.data.paths import DEFAULT_STORAGE_PATHS


class ColdEventArchive:
    """Append-only durable history of accepted short-term events."""

    def __init__(
        self,
        path: str | Path = DEFAULT_STORAGE_PATHS.cold_archive_events,
    ) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Return the configured JSONL archive path."""

        return self._path

    def archive(
        self,
        event: ShortTermEvent,
        *,
        archived_at: str | None = None,
    ) -> ArchivedEvent:
        """Archive a short-term event directly in the cold site."""

        if not isinstance(event, ShortTermEvent):
            raise TypeError("event must be a ShortTermEvent.")

        archived_event = ArchivedEvent.from_short_term_event(
            event,
            archived_at=archived_at,
        )

        append_json_line(
            self._path,
            archived_event.to_dict(),
        )

        return archived_event

    def list_events(self) -> tuple[ArchivedEvent, ...]:
        """Load the complete durable event history."""

        return tuple(
            ArchivedEvent.from_dict(payload)
            for payload in read_json_lines(self._path)
        )

    def get_by_id(self, event_id: str) -> ArchivedEvent | None:
        """Return the latest archived representation of an event ID."""

        for event in reversed(self.list_events()):
            if event.event_id == event_id:
                return event

        return None

    def contains(self, event_id: str) -> bool:
        """Report whether an event is already archived."""

        return self.get_by_id(event_id) is not None
