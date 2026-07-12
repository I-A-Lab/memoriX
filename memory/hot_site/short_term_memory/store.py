"""JSONL-backed short-term event storage."""

from __future__ import annotations

from pathlib import Path

from memory.data import ShortTermEvent
from memory.data.jsonl_store import (
    append_json_line,
    read_json_lines,
    rewrite_json_lines,
)
from memory.data.paths import DEFAULT_STORAGE_PATHS


class ShortTermEventStore:
    """Persist and load recent memory events."""

    def __init__(
        self,
        path: str | Path = DEFAULT_STORAGE_PATHS.short_term_events,
    ) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Return the configured JSONL path."""

        return self._path

    def append(self, event: ShortTermEvent) -> ShortTermEvent:
        """Append one recent event and return it unchanged."""

        if not isinstance(event, ShortTermEvent):
            raise TypeError("event must be a ShortTermEvent.")

        append_json_line(self._path, event.to_dict())
        return event

    def list_events(self) -> tuple[ShortTermEvent, ...]:
        """Load all stored short-term events in insertion order."""

        return tuple(
            ShortTermEvent.from_dict(payload)
            for payload in read_json_lines(self._path)
        )

    def get_by_id(self, event_id: str) -> ShortTermEvent | None:
        """Return one event by ID, or None when it is absent."""

        for event in reversed(self.list_events()):
            if event.event_id == event_id:
                return event

        return None

    def contains(self, event_id: str) -> bool:
        """Report whether an event ID already exists."""

        return self.get_by_id(event_id) is not None

    def clear(self) -> int:
        """Remove all recent events and return the previous count."""

        events = self.list_events()
        rewrite_json_lines(self._path, ())
        return len(events)
