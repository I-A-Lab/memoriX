"""Append-only storage for non-applied adaptive-controller decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from memory.adaptive.contracts import (
    AdaptiveControllerDecision,
)


class AdaptiveDecisionStore:
    """JSONL history restricted to safe dry-run controller outputs."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        decision: AdaptiveControllerDecision,
    ) -> None:
        if not decision.observation_only:
            raise ValueError(
                "Only observation-only decisions may be stored."
            )

        if not decision.dry_run or decision.applied:
            raise ValueError(
                "Only non-applied dry-run decisions may be stored."
            )

        if not decision.hot_site_only:
            raise ValueError(
                "Adaptive decisions must remain hot-site only."
            )

        if not decision.cold_site_untouched:
            raise ValueError(
                "Cold-site mutation is forbidden."
            )

        if decision.retrieval_behavior_changed:
            raise ValueError(
                "Retrieval changes are forbidden."
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
                    decision.to_dict(),
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
                        "Invalid adaptive-decision JSON "
                        f"at line {line_number}."
                    ) from exc

                if not isinstance(value, dict):
                    raise ValueError(
                        "Adaptive-decision records "
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
