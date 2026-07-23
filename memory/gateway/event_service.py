"""Gateway service for recording short-term events and cold history."""

from __future__ import annotations

from dataclasses import dataclass

from memory.cold_site.long_term_store import ColdEventArchive
from memory.data import ArchivedEvent, ShortTermEvent
from memory.hot_site.short_term_memory import ShortTermEventStore


class DuplicateEventError(ValueError):
    """Raised when an event ID already exists in either destination."""


class MemoryEventConsistencyError(RuntimeError):
    """Raised when short-term and cold-site state are inconsistent."""


@dataclass(frozen=True, slots=True)
class RecordedMemoryEvent:
    """Result of one successful direct hot/cold event recording."""

    short_term_event: ShortTermEvent
    archived_event: ArchivedEvent


class MemoryEventService:
    """Coordinate the direct short-term and cold-archive event path.

    This service does not perform consolidation, candidate creation,
    validation, Titan storage, retrieval, or MCP communication.
    """

    def __init__(
        self,
        short_term_store: ShortTermEventStore,
        cold_archive: ColdEventArchive,
    ) -> None:
        self._short_term_store = short_term_store
        self._cold_archive = cold_archive

    def record_event(
        self,
        event: ShortTermEvent,
        *,
        archived_at: str | None = None,
    ) -> RecordedMemoryEvent:
        """Write one event to short-term and directly to cold history.

        Duplicate IDs are rejected before either write. The cold archive is
        intentionally append-only. This first storage implementation performs
        two coordinated writes but does not claim full filesystem transaction
        semantics.
        """

        if not isinstance(event, ShortTermEvent):
            raise TypeError("event must be a ShortTermEvent.")

        in_short_term = self._short_term_store.contains(event.event_id)
        in_cold_archive = self._cold_archive.contains(event.event_id)

        if in_short_term != in_cold_archive:
            raise MemoryEventConsistencyError(
                "Event ID exists in only one storage destination: "
                f"{event.event_id}"
            )

        if in_short_term:
            raise DuplicateEventError(
                f"Event ID already exists: {event.event_id}"
            )

        stored_event = self._short_term_store.append(event)

        try:
            archived_event = self._cold_archive.archive(
                event,
                archived_at=archived_at,
            )
        except Exception as error:
            raise MemoryEventConsistencyError(
                "Short-term write succeeded but cold archival failed for "
                f"event {event.event_id}. Manual recovery is required."
            ) from error

        return RecordedMemoryEvent(
            short_term_event=stored_event,
            archived_event=archived_event,
        )
