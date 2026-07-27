"""
Neural Titan backend for memoriX.

This backend connects the controlled memory API to the real TitanExternalMemory
implemented in titan_model.py.

Important:
- Agents still do not write directly into Titan.
- This backend only stores already validated long-term memories.
- Metadata is kept in a JSONL sidecar because TitanExternalMemory mainly stores
  neural/structured memory items.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os


DEFAULT_TITAN_NEURAL_PATH = (
    Path("memory") / "hot_site" / "titan_active_memory" / "data" / "titan_memory.pt"
)
DEFAULT_TITAN_METADATA_PATH = (
    Path("memory") / "hot_site" / "titan_active_memory" / "data" / "titan_metadata.jsonl"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: str | Path, item: Dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    file_path = Path(path)

    if not file_path.exists():
        return []

    items: List[Dict[str, Any]] = []

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return items


def _rewrite_jsonl(path: str | Path, items: List[Dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


class NeuralTitanBackend:
    """
    Adapter around TitanExternalMemory from titan_model.py.

    It stores validated long-term memories in the real Titan model while keeping
    metadata in a small sidecar file.
    """

    def __init__(
        self,
        memory_path: str | Path = DEFAULT_TITAN_NEURAL_PATH,
        metadata_path: str | Path = DEFAULT_TITAN_METADATA_PATH,
        d_model: int = 128,
        hidden_dim: int = 256,
        max_items: int = 5000,
        device: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.12,
    ) -> None:
        self.memory_path = Path(memory_path)
        self.metadata_path = Path(metadata_path)
        self.d_model = int(d_model)
        self.hidden_dim = int(hidden_dim)
        self.max_items = int(max_items)
        self.device = device or os.getenv("MEMORIX_TITAN_DEVICE", os.getenv("TITAN_DEVICE", "cpu"))
        self.top_k = int(top_k)
        self.min_score = float(min_score)

        try:
            from memory.hot_site.titan_active_memory.titan_model import TitanExternalMemory
        except Exception as exc:
            raise RuntimeError(
                "Could not import TitanExternalMemory from "
                "memory.hot_site.titan_active_memory.titan_model. Check titan_model.py and "
                "dependencies such as torch."
            ) from exc

        self.memory = TitanExternalMemory(
            memory_path=self.memory_path,
            d_model=self.d_model,
            hidden_dim=self.hidden_dim,
            max_items=self.max_items,
            device=self.device,
            use_aedelon_ltm=True,
        )

    def store_validated_memory(
        self,
        memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store an already validated memory into the real TitanExternalMemory.
        """

        if not memory.get("id"):
            raise ValueError("Validated memory must have an id.")

        if not memory.get("content"):
            raise ValueError("Validated memory must have content.")

        if not memory.get("validated_by"):
            raise ValueError("Validated memory must specify validated_by.")

        content = str(memory["content"])

        results = self.memory.store_text(content)

        titan_item_ids: List[int] = []

        for _action, item, _deactivated in results:
            titan_item_ids.append(int(item.id))

        self.memory.save(self.memory_path)

        metadata_record = {
            "memory_id": memory["id"],
            "content": content,
            "source_agent": memory.get("source_agent"),
            "validated_by": memory.get("validated_by"),
            "validation_reason": memory.get("validation_reason"),
            "metadata": memory.get("metadata", {}),
            "titan_item_ids": titan_item_ids,
            "titan_memory_path": str(self.memory_path),
            "stored_at": utc_now(),
            "active": memory.get("active", True),
        }

        _append_jsonl(self.metadata_path, metadata_record)

        output = dict(memory)
        output["titan_backend"] = "titan_external"
        output["titan_item_ids"] = titan_item_ids
        output["titan_memory_path"] = str(self.memory_path)
        output["metadata_path"] = str(self.metadata_path)

        return output

    def _metadata_by_content(self) -> Dict[str, Dict[str, Any]]:
        records = _read_jsonl(self.metadata_path)

        by_content: Dict[str, Dict[str, Any]] = {}

        for record in records:
            content = record.get("content", "")

            if content:
                by_content[content] = record

        return by_content


    def _metadata_by_titan_item_id(self) -> Dict[int, Dict[str, Any]]:
        records = _read_jsonl(self.metadata_path)

        by_item_id: Dict[int, Dict[str, Any]] = {}

        for record in records:
            for titan_item_id in record.get("titan_item_ids", []) or []:
                try:
                    by_item_id[int(titan_item_id)] = record
                except (TypeError, ValueError):
                    continue

        return by_item_id

    def _allowed_titan_item_ids(
        self,
        *,
        project_id: str | None,
        user_id: str | None,
    ) -> set[int] | None:
        """Return Titan item ids allowed by exact metadata scope filters."""

        if project_id is None and user_id is None:
            return None

        allowed: set[int] = set()
        for record in _read_jsonl(self.metadata_path):
            if record.get("active", True) is False:
                continue

            metadata = dict(record.get("metadata") or {})
            if (
                project_id is not None
                and metadata.get("project_id") != project_id
            ):
                continue
            if (
                user_id is not None
                and metadata.get("user_id") != user_id
            ):
                continue

            for raw_item_id in record.get("titan_item_ids", []) or []:
                try:
                    allowed.add(int(raw_item_id))
                except (TypeError, ValueError):
                    continue

        return allowed

    def retrieve(
        self,
        query: str,
        role: str | None = None,
        top_k: int | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories from the real TitanExternalMemory.

        Optional project and user filters are exact metadata constraints. They
        restrict the candidate set before Titan scores and ranks memories.
        """

        k = self.top_k if top_k is None else int(top_k)
        allowed_item_ids = self._allowed_titan_item_ids(
            project_id=project_id,
            user_id=user_id,
        )

        retrieved = self.memory.retrieve(
            query=query,
            k=k,
            min_score=self.min_score,
            allowed_item_ids=allowed_item_ids,
        )

        metadata_by_content = self._metadata_by_content()
        metadata_by_item_id = self._metadata_by_titan_item_id()

        results: List[Dict[str, Any]] = []

        for score, details, item in retrieved:
            item_id = int(item.id)
            item_active = bool(getattr(item, "active", True))
            metadata_record = metadata_by_item_id.get(item_id) or metadata_by_content.get(item.text, {})
            record_active = metadata_record.get("active", item_active)

            # A soft-forgotten validated memory must not be returned as an
            # active retrieval result. Titan stores internal neural items, but
            # the gateway works with validated memory ids, so both levels are
            # checked here.
            if record_active is False or not item_active:
                continue

            memory_id = (
                metadata_record.get("memory_id")
                or metadata_record.get("id")
                or f"titan_item_{item_id}"
            )

            result = {
                "id": memory_id,
                "memory_id": memory_id,
                "content": item.text,
                "source_agent": metadata_record.get("source_agent", "unknown"),
                "validated_by": metadata_record.get("validated_by", "unknown"),
                "metadata": metadata_record.get("metadata", {}),
                "active": bool(record_active),
                "titan_backend": "titan_external",
                "titan_item_id": item_id,
                "score": float(score),
                "details": details,
                "subject": getattr(item, "subject", None),
                "property": getattr(item, "property", None),
            }

            if role:
                roles = result.get("metadata", {}).get("roles", [])

                if roles and role not in roles:
                    continue

            results.append(result)

        self.memory.save(self.memory_path)

        return results


    def stats(self) -> Dict[str, Any]:
        """Return runtime statistics from the underlying TitanExternalMemory."""

        stats = self.memory.stats()
        return {
            **stats,
            "backend": "titan_external",
            "metadata_path": str(self.metadata_path),
            "configured_top_k": self.top_k,
            "configured_min_score": self.min_score,
        }

    def list_metadata(self) -> List[Dict[str, Any]]:
        """
        List sidecar metadata records.

        This is not the same as listing every internal Titan item.
        """

        return _read_jsonl(self.metadata_path)

    def soft_forget(
        self,
        memory_id: str,
        validated_by: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Soft-forget a validated memory by deactivating related Titan items.
        """

        metadata_records = _read_jsonl(self.metadata_path)

        matching_records = [
            record
            for record in metadata_records
            if record.get("memory_id") == memory_id
        ]

        if not matching_records:
            raise ValueError(f"No Titan metadata found for memory id: {memory_id}")

        titan_item_ids: List[int] = []

        for record in matching_records:
            titan_item_ids.extend(record.get("titan_item_ids", []))

        changed_items = self.memory.deactivate_ids(
            titan_item_ids,
            reason=reason or f"forgotten by {validated_by}",
        )

        self.memory.save(self.memory_path)

        updated_metadata_records: List[Dict[str, Any]] = []
        forgotten_at = utc_now()

        for record in metadata_records:
            record = dict(record)
            if record.get("memory_id") == memory_id:
                record["active"] = False
                record["forgotten_by"] = validated_by
                record["forget_reason"] = reason
                record["forgotten_at"] = forgotten_at
            updated_metadata_records.append(record)

        _rewrite_jsonl(self.metadata_path, updated_metadata_records)

        forget_record = {
            "memory_id": memory_id,
            "forgotten_by": validated_by,
            "forget_reason": reason,
            "forgotten_at": utc_now(),
            "titan_item_ids": titan_item_ids,
            "changed_items": [int(item.id) for item in changed_items],
        }

        _append_jsonl(
            self.metadata_path.with_name("titan_forget_log.jsonl"),
            forget_record,
        )

        return {
            "memory_id": memory_id,
            "active": False,
            "forgotten_by": validated_by,
            "reason": reason,
            "titan_item_ids": titan_item_ids,
            "changed_items": [int(item.id) for item in changed_items],
        }
