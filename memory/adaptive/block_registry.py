"""Explicit and isolated registry for observed dynamic topic blocks.

The registry stores observations only. It does not route candidates, resize
Titan, prune memories, read cold history, or alter the public gateway.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from memory.adaptive.contracts import (
    TopicBlockObservation,
)


class TopicBlockRegistry:
    """JSON registry for merged topic-block observations."""

    SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {
                "schema_version": TopicBlockRegistry.SCHEMA_VERSION,
                "observation_only": True,
                "blocks": [],
            }

        try:
            value = json.loads(
                self._path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid topic-block registry JSON."
            ) from exc

        if not isinstance(value, dict):
            raise ValueError(
                "Topic-block registry must be a JSON object."
            )

        if value.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError(
                "Unsupported topic-block registry schema version."
            )

        blocks = value.get("blocks")

        if not isinstance(blocks, list):
            raise ValueError(
                "Topic-block registry blocks must be a list."
            )

        return value

    def blocks(self) -> list[dict[str, Any]]:
        return list(self.read()["blocks"])

    def get(
        self,
        block_id: str,
    ) -> dict[str, Any] | None:
        for block in self.blocks():
            if block.get("block_id") == block_id:
                return block

        return None

    def upsert_observation(
        self,
        observation: TopicBlockObservation,
    ) -> dict[str, Any]:
        state = self.read()
        blocks = list(state["blocks"])

        existing_index = next(
            (
                index
                for index, block in enumerate(blocks)
                if block.get("block_id")
                == observation.block_id
            ),
            None,
        )

        incoming = observation.to_dict()

        if existing_index is None:
            incoming["observation_count"] = 1
            blocks.append(incoming)
            merged = incoming
        else:
            merged = self._merge(
                blocks[existing_index],
                incoming,
            )
            blocks[existing_index] = merged

        blocks.sort(
            key=lambda block: str(
                block.get("block_id", "")
            )
        )

        self._write(
            {
                "schema_version": TopicBlockRegistry.SCHEMA_VERSION,
                "observation_only": True,
                "blocks": blocks,
            }
        )

        return merged

    def _write(
        self,
        state: Mapping[str, Any],
    ) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self._path.with_suffix(
            self._path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(self._path)

    @staticmethod
    def _merge(
        existing: Mapping[str, Any],
        incoming: Mapping[str, Any],
    ) -> dict[str, Any]:
        frequencies: Counter[str] = Counter()

        for block in (existing, incoming):
            terms = block.get("terms", [])

            if not isinstance(terms, list):
                continue

            for term in terms:
                if not isinstance(term, dict):
                    continue

                name = term.get("term")
                count = term.get("count")

                if (
                    isinstance(name, str)
                    and isinstance(count, int)
                    and count > 0
                ):
                    frequencies[name] += count

        maximum_count = max(
            frequencies.values(),
            default=1,
        )

        merged_terms = [
            {
                "term": term,
                "count": count,
                "weight": min(
                    1.0,
                    count / maximum_count,
                ),
            }
            for term, count in sorted(
                frequencies.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            )[:20]
        ]

        existing_ids = existing.get(
            "observed_item_ids",
            [],
        )
        incoming_ids = incoming.get(
            "observed_item_ids",
            [],
        )

        item_ids = sorted(
            {
                str(item_id)
                for item_id in [
                    *(
                        existing_ids
                        if isinstance(existing_ids, list)
                        else []
                    ),
                    *(
                        incoming_ids
                        if isinstance(incoming_ids, list)
                        else []
                    ),
                ]
                if str(item_id).strip()
            }
        )

        existing_count = int(
            existing.get(
                "observation_count",
                1,
            )
        )

        incoming_importance = float(
            incoming.get(
                "importance",
                0.0,
            )
        )

        existing_importance = float(
            existing.get(
                "importance",
                0.0,
            )
        )

        observation_count = existing_count + 1

        average_importance = (
            existing_importance
            * existing_count
            + incoming_importance
        ) / observation_count

        capacity = max(
            int(existing.get("capacity", 1)),
            int(incoming.get("capacity", 1)),
        )

        used_items = len(item_ids)

        return {
            "block_id": incoming["block_id"],
            "label": incoming["label"],
            "terms": merged_terms,
            "capacity": capacity,
            "used_items": used_items,
            "usage_ratio": min(
                1.0,
                used_items / capacity,
            ),
            "importance": average_importance,
            "observed_item_ids": item_ids,
            "created_at": existing.get(
                "created_at",
                incoming["created_at"],
            ),
            "updated_at": incoming["updated_at"],
            "routing": incoming["routing"],
            "schema_version": TopicBlockRegistry.SCHEMA_VERSION,
            "observation_only": True,
            "observation_count": observation_count,
        }

    def iter_blocks(
        self,
    ) -> Iterable[dict[str, Any]]:
        yield from self.blocks()
