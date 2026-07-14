"""Optional JSONL persistence for pressure observations.

The store is not connected to the gateway during Part 12B. Callers must pass
an explicit path, normally inside a temporary runtime or a future adaptive
directory managed by MemoryStoragePaths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from memory.adaptive.contracts import (
    PressureObservation,
)


class PressureHistoryStore:
    """Append-only JSONL store for observable pressure results."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        observation: PressureObservation,
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        line = json.dumps(
            observation.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
        )

        with self._path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(line)
            handle.write("\n")

    def read_all(self) -> list[dict]:
        if not self._path.exists():
            return []

        records: list[dict] = []

        with self._path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line_number, raw_line in enumerate(
                handle,
                start=1,
            ):
                line = raw_line.strip()

                if not line:
                    continue

                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        "Invalid pressure-history JSON "
                        f"at line {line_number}."
                    ) from exc

                if not isinstance(value, dict):
                    raise ValueError(
                        "Pressure-history records "
                        "must be JSON objects."
                    )

                records.append(value)

        return records

    def iter_scope(
        self,
        scope_id: str,
    ) -> Iterable[dict]:
        for record in self.read_all():
            if record.get("scope_id") == scope_id:
                yield record
