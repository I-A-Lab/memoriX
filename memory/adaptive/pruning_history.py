"""Append-only history for non-applied soft-pruning plans."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from memory.adaptive.contracts import (
    SoftPruningPlan,
)


class SoftPruningPlanStore:
    """JSONL storage restricted to dry-run, non-applied plans."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        plan: SoftPruningPlan,
    ) -> None:
        if not plan.hot_site_only:
            raise ValueError(
                "Only hot-site pruning plans may be stored."
            )

        if not plan.cold_site_untouched:
            raise ValueError(
                "Cold-site mutations are forbidden."
            )

        if plan.physical_deletion:
            raise ValueError(
                "Physical-deletion plans are forbidden."
            )

        if not plan.dry_run or plan.applied:
            raise ValueError(
                "Only non-applied dry-run plans may be stored."
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
                    plan.to_dict(),
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
                        "Invalid pruning-history JSON "
                        f"at line {line_number}."
                    ) from exc

                if not isinstance(value, dict):
                    raise ValueError(
                        "Pruning-history records "
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
