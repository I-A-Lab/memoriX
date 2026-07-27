"""Controlled typed interface for the active Titan hot site.

This adapter connects the new memoriX domain contracts to the historical
neural Titan backend.

Only already validated memories may enter this component. This module never
reads from or writes to the cold site.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from memory.data import (
    ForgetAction,
    ForgetResult,
    RetrievalResult,
    RetrievalSource,
    RetrievedMemory,
    ValidatedMemory,
)
from memory.data.paths import DEFAULT_STORAGE_PATHS
from memory.hot_site.titan_active_memory.neural_backend import (
    NeuralTitanBackend,
)


def _deduplicate_retrieved_matches(
    matches: list,
) -> list:
    """Keep one highest-scoring result for each logical memory ID."""

    best_by_memory_id = {}
    memory_order = []

    for match in matches:
        memory_id = match.memory_id
        current = best_by_memory_id.get(memory_id)

        if current is None:
            best_by_memory_id[memory_id] = match
            memory_order.append(memory_id)
            continue

        if match.score > current.score:
            best_by_memory_id[memory_id] = match

    return [
        best_by_memory_id[memory_id]
        for memory_id in memory_order
    ]

class HotSiteInputError(ValueError):
    """Raised when data violates the active hot-site contract."""


class HotSiteTitanMemory:
    """Typed active-memory interface backed by the neural Titan engine."""

    def __init__(
        self,
        *,
        neural_state_path: str | Path = (
            DEFAULT_STORAGE_PATHS.titan_neural_state
        ),
        metadata_path: str | Path = (
            DEFAULT_STORAGE_PATHS.titan_metadata
        ),
        d_model: int = 256,
        hidden_dim: int = 256,
        max_items: int = 50_000,
        device: str = "cpu",
        top_k: int = 5,
        min_score: float = 0.12,
    ) -> None:
        if d_model <= 0:
            raise ValueError("d_model must be positive.")

        if hidden_dim <= 0:
            raise ValueError("hidden_dim must be positive.")

        if max_items <= 0:
            raise ValueError("max_items must be positive.")

        if top_k <= 0:
            raise ValueError("top_k must be positive.")

        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0.0 and 1.0.")

        self._neural_state_path = Path(neural_state_path)
        self._metadata_path = Path(metadata_path)

        self._backend = NeuralTitanBackend(
            memory_path=self._neural_state_path,
            metadata_path=self._metadata_path,
            d_model=d_model,
            hidden_dim=hidden_dim,
            max_items=max_items,
            device=device,
            top_k=top_k,
            min_score=min_score,
        )

    @property
    def neural_state_path(self) -> Path:
        """Return the Titan neural-state file path."""

        return self._neural_state_path

    @property
    def metadata_path(self) -> Path:
        """Return the validated-memory metadata path."""

        return self._metadata_path

    def store_validated(
        self,
        memory: ValidatedMemory,
        *,
        validated_by: str,
        validation_reason: str = "",
    ) -> ValidatedMemory:
        """Store one already validated memory in the active hot site."""

        if not isinstance(memory, ValidatedMemory):
            raise TypeError("memory must be a ValidatedMemory.")

        if not memory.active:
            raise HotSiteInputError(
                "An inactive memory cannot be inserted into Titan."
            )

        reviewer = validated_by.strip()

        if not reviewer:
            raise HotSiteInputError(
                "validated_by must not be empty."
            )

        metadata = dict(memory.metadata)
        metadata.update(
            {
                "source_candidate_id": memory.source_candidate_id,
                "created_at": memory.created_at,
                "validated_at": memory.validated_at,
                "version": memory.version,
                "supersedes_memory_id": (
                    memory.supersedes_memory_id
                ),
                "active": memory.active,
                "validated": True,
            }
        )

        payload: dict[str, Any] = {
            "id": memory.memory_id,
            "content": memory.content,
            "source_agent": metadata.get(
                "source_agent",
                "memorix_validation",
            ),
            "validated_by": reviewer,
            "validation_reason": validation_reason,
            "active": True,
            "metadata": metadata,
        }

        self._backend.store_validated_memory(payload)

        return memory

    def list_memories(
        self,
        *,
        active_only: bool = False,
    ) -> tuple[ValidatedMemory, ...]:
        """List validated memories represented by Titan metadata."""

        records = self._backend.list_metadata()
        latest_by_id: dict[str, dict[str, Any]] = {}

        for record in records:
            memory_id = str(
                record.get("memory_id")
                or record.get("id")
                or ""
            ).strip()

            if memory_id:
                latest_by_id[memory_id] = record

        memories: list[ValidatedMemory] = []

        for memory_id, record in latest_by_id.items():
            metadata = dict(record.get("metadata") or {})
            active = bool(record.get("active", True))

            if active_only and not active:
                continue

            memories.append(
                ValidatedMemory(
                    memory_id=memory_id,
                    content=str(record.get("content") or ""),
                    source_candidate_id=str(
                        metadata.get(
                            "source_candidate_id",
                            "legacy_candidate_unknown",
                        )
                    ),
                    created_at=str(
                        metadata.get("created_at")
                        or record.get("stored_at")
                    ),
                    validated_at=str(
                        metadata.get("validated_at")
                        or record.get("stored_at")
                    ),
                    active=active,
                    version=int(metadata.get("version", 1)),
                    supersedes_memory_id=(
                        str(metadata["supersedes_memory_id"])
                        if metadata.get(
                            "supersedes_memory_id"
                        ) is not None
                        else None
                    ),
                    metadata=metadata,
                )
            )

        return tuple(memories)

    def retrieve(
        self,
        query: str,
        *,
        role: str | None = None,
        top_k: int | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> RetrievalResult:
        """Retrieve active memories from Titan only.

        Scope filters are exact metadata constraints applied before ranking.
        Omitting both filters preserves the historical global retrieval path.
        """

        if not isinstance(query, str) or not query.strip():
            raise HotSiteInputError(
                "query must not be empty."
            )

        if top_k is not None and top_k <= 0:
            raise HotSiteInputError(
                "top_k must be positive."
            )

        normalized_project_id = (
            project_id.strip()
            if project_id is not None
            else None
        )
        normalized_user_id = (
            user_id.strip()
            if user_id is not None
            else None
        )
        if project_id is not None and not normalized_project_id:
            raise HotSiteInputError(
                "project_id must not be empty when provided."
            )
        if user_id is not None and not normalized_user_id:
            raise HotSiteInputError(
                "user_id must not be empty when provided."
            )

        backend_results = self._backend.retrieve(
            query=query,
            role=role,
            top_k=top_k,
            project_id=normalized_project_id,
            user_id=normalized_user_id,
        )

        matches: list[RetrievedMemory] = []

        for result in backend_results:
            raw_score = float(result.get("score", 0.0))
            normalized_score = min(1.0, max(0.0, raw_score))

            metadata = dict(result.get("metadata") or {})
            metadata.update(
                {
                    "active": bool(
                        result.get("active", True)
                    ),
                    "titan_backend": result.get(
                        "titan_backend",
                        "titan_external",
                    ),
                    "titan_item_id": result.get(
                        "titan_item_id"
                    ),
                }
            )

            result_subject = result.get("subject")

            if (
                metadata.get("subject") is None
                and result_subject is not None
            ):
                metadata["subject"] = result_subject

            result_property = result.get("property")

            if (
                metadata.get("property") is None
                and result_property is not None
            ):
                metadata["property"] = result_property

            matches.append(
                RetrievedMemory(
                    memory_id=str(
                        result.get("memory_id")
                        or result.get("id")
                    ),
                    content=str(result.get("content") or ""),
                    score=normalized_score,
                    metadata=metadata,
                )
            )

        return RetrievalResult(
            query=query,
            source=RetrievalSource.HOT_SITE,
            matches=tuple(_deduplicate_retrieved_matches(matches)),
        )

    def soft_forget(
        self,
        memory_id: str,
        *,
        validated_by: str,
        reason: str,
    ) -> ForgetResult:
        """Deactivate one memory in the hot site only."""

        identifier = memory_id.strip()
        reviewer = validated_by.strip()
        explanation = reason.strip()

        if not identifier:
            raise HotSiteInputError(
                "memory_id must not be empty."
            )

        if not reviewer:
            raise HotSiteInputError(
                "validated_by must not be empty."
            )

        if not explanation:
            raise HotSiteInputError(
                "reason must not be empty."
            )

        try:
            self._backend.soft_forget(
                memory_id=identifier,
                validated_by=reviewer,
                reason=explanation,
            )
        except ValueError:
            return ForgetResult(
                memory_id=identifier,
                action=ForgetAction.NOT_FOUND,
                reason=explanation,
            )

        return ForgetResult(
            memory_id=identifier,
            action=ForgetAction.DEACTIVATED,
            reason=explanation,
        )

    def compute_surprise(self, text: str) -> float:
        """Compute a normalized Titan surprise score without storing text.

        Titan exposes a raw prediction-error value. The raw value is converted
        to the closed interval [0, 1] with a smooth saturating function.

        This operation does not create a validated memory and does not write
        to either the hot-site metadata store or the cold site.
        """

        if not isinstance(text, str) or not text.strip():
            raise HotSiteInputError(
                "text must not be empty."
            )

        try:
            titan_memory = self._backend.memory
            key, value = titan_memory._make_key_value(text)
            raw_surprise = float(
                titan_memory._surprise(key, value)
            )
        except Exception as error:
            raise RuntimeError(
                "Titan surprise computation failed."
            ) from error

        if raw_surprise <= 0.0:
            return 0.0

        normalized = raw_surprise / (
            raw_surprise + 0.015
        )

        return min(1.0, max(0.0, normalized))

    def replay_active_memories(
        self,
        *,
        replayed_by: str = "memorix_nightly",
        replay_reason: str = "Nightly active-memory replay.",
    ) -> int:
        """Replay all active validated memories through Titan.

        Replay reinforces the active neural memory only. It does not read,
        write, or modify the cold site, and it does not validate candidates.
        """

        reviewer = replayed_by.strip()
        reason = replay_reason.strip()

        if not reviewer:
            raise HotSiteInputError(
                "replayed_by must not be empty."
            )

        if not reason:
            raise HotSiteInputError(
                "replay_reason must not be empty."
            )

        active_memories = self.list_memories(
            active_only=True
        )

        for memory in active_memories:
            metadata = dict(memory.metadata)
            metadata.update(
                {
                    "source_candidate_id": (
                        memory.source_candidate_id
                    ),
                    "created_at": memory.created_at,
                    "validated_at": memory.validated_at,
                    "version": memory.version,
                    "supersedes_memory_id": (
                        memory.supersedes_memory_id
                    ),
                    "active": True,
                    "validated": True,
                    "nightly_replay": True,
                }
            )

            payload: dict[str, Any] = {
                "id": memory.memory_id,
                "content": memory.content,
                "source_agent": metadata.get(
                    "source_agent",
                    "memorix_nightly",
                ),
                "validated_by": reviewer,
                "validation_reason": reason,
                "active": True,
                "metadata": metadata,
            }

            self._backend.store_validated_memory(
                payload
            )

        return len(active_memories)

    def stats(self) -> dict[str, Any]:
        """Return statistics from the underlying Titan backend."""

        return dict(self._backend.stats())
