"""Append-only history for dry-run capacity recommendations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from memory.adaptive.contracts import (
    CapacityRecommendation,
)


class CapacityRecommendationStore:
    """JSONL store that never applies the recorded recommendations."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        recommendation: CapacityRecommendation,
    ) -> None:
        if not recommendation.dry_run:
            raise ValueError(
                "Only dry-run recommendations may be stored."
            )

        if recommendation.applied:
            raise ValueError(
                "Applied recommendations are forbidden in 12E."
            )

        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self._path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(
                json.dumps(
                    recommendation.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
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
                        "Invalid capacity-history JSON "
                        f"at line {line_number}."
                    ) from exc

                if not isinstance(value, dict):
                    raise ValueError(
                        "Capacity-history records "
                        "must be JSON objects."
                    )

                records.append(value)

        return records

    def iter_block(
        self,
        block_id: str,
    ) -> Iterable[dict]:
        for record in self.read_all():
            if record.get("block_id") == block_id:
                yield record
