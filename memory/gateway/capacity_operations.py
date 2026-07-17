"""Operational journal and lock for capacity actions."""
from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class CapacityOperationLockedError(RuntimeError):
    """Raised when another capacity mutation owns the lock."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapacityOperations:
    def __init__(self, *, lock_path: Path, events_path: Path, latest_path: Path) -> None:
        self.lock_path = Path(lock_path)
        self.events_path = Path(events_path)
        self.latest_path = Path(latest_path)

    def record(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_id": f"capacity_event_{uuid.uuid4().hex}",
            "event_type": event_type,
            "observed_at": _now(),
            **payload,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        tmp = self.latest_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(event, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(tmp, self.latest_path)
        return event

    @contextmanager
    def mutation_lock(self, operation: str) -> Iterator[str]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise CapacityOperationLockedError(
                "A capacity mutation is already running."
            ) from error
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    {"token": token, "operation": operation, "created_at": _now()},
                    handle,
                    sort_keys=True,
                )
                handle.write("\n")
            yield token
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
