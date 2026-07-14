"""Human candidate-review gateway for the Titan hot site."""

from __future__ import annotations

from memory.gateway.adaptive_validation import (
    AdaptiveValidationMetadataService,
)

from dataclasses import replace

from memory.consolidation.candidate_store import (
    MemoryCandidateStore,
)
from memory.data import (
    CandidateStatus,
    ForgetAction,
    MemoryCandidate,
    ValidatedMemory,
    utc_now_iso,
)
from memory.hot_site.titan_active_memory import (
    HotSiteTitanMemory,
)


class CandidateValidationError(RuntimeError):
    """Raised when candidate validation cannot be completed safely."""


class MemoryValidationService:
    """Validate or reject candidates through an explicit human action."""

    def __init__(
        self,
        candidate_store: MemoryCandidateStore,
        hot_site: HotSiteTitanMemory,
    ) -> None:
        self._candidate_store = candidate_store
        self._hot_site = hot_site

    def validate(
        self,
        candidate_id: str,
        *,
        validated_by: str,
        validation_reason: str,
        final_content: str | None = None,
    ) -> ValidatedMemory:
        """Validate one pending candidate and store it in Titan only."""

        reviewer = validated_by.strip()
        explanation = validation_reason.strip()

        if not reviewer:
            raise ValueError("validated_by must not be empty.")

        if not explanation:
            raise ValueError(
                "validation_reason must not be empty."
            )

        candidate = self._candidate_store.require_pending(
            candidate_id
        )

        content = (
            final_content.strip()
            if final_content is not None
            else candidate.content
        )

        if not content:
            raise ValueError(
                "Validated memory content must not be empty."
            )

        superseded_memory = None
        version = 1

        if candidate.target_memory_id is not None:
            existing = {
                memory.memory_id: memory
                for memory in self._hot_site.list_memories()
            }
            superseded_memory = existing.get(
                candidate.target_memory_id
            )

            if superseded_memory is None:
                raise CandidateValidationError(
                    "The candidate targets an unknown hot-site "
                    f"memory: {candidate.target_memory_id}"
                )

            version = superseded_memory.version + 1

        validated_memory = ValidatedMemory(
            content=content,
            source_candidate_id=candidate.candidate_id,
            validated_at=utc_now_iso(),
            active=True,
            version=version,
            supersedes_memory_id=(
                superseded_memory.memory_id
                if superseded_memory is not None
                else None
            ),
            metadata=AdaptiveValidationMetadataService().enrich(
                         candidate_id=candidate.candidate_id,
                         content=candidate.content,
                         metadata=(
                             {**candidate.metadata, 'candidate_reason': candidate.reason, 'source_event_ids': list(candidate.source_event_ids), 'importance': candidate.importance, 'confidence': candidate.confidence, 'surprise': candidate.surprise, 'validated_by': reviewer, 'validation_reason': explanation}
                         ),
                         importance=candidate.importance,
                         observed_at=candidate.created_at,
                     ),
        )

        self._hot_site.store_validated(
            validated_memory,
            validated_by=reviewer,
            validation_reason=explanation,
        )

        if superseded_memory is not None:
            forget_result = self._hot_site.soft_forget(
                superseded_memory.memory_id,
                validated_by=reviewer,
                reason=(
                    "Superseded by validated memory "
                    f"{validated_memory.memory_id}."
                ),
            )

            if forget_result.action is not ForgetAction.DEACTIVATED:
                raise CandidateValidationError(
                    "The replacement memory was stored, but the "
                    "superseded hot-site memory was not deactivated."
                )

        validated_candidate = replace(
            candidate,
            status=CandidateStatus.VALIDATED,
            metadata={
                **candidate.metadata,
                "validated_memory_id": (
                    validated_memory.memory_id
                ),
                "validated_by": reviewer,
                "validation_reason": explanation,
                "reviewed_at": validated_memory.validated_at,
            },
        )

        self._candidate_store.replace(validated_candidate)

        return validated_memory

    def reject(
        self,
        candidate_id: str,
        *,
        rejected_by: str,
        rejection_reason: str,
    ) -> MemoryCandidate:
        """Reject one pending candidate without touching Titan."""

        reviewer = rejected_by.strip()
        explanation = rejection_reason.strip()

        if not reviewer:
            raise ValueError("rejected_by must not be empty.")

        if not explanation:
            raise ValueError(
                "rejection_reason must not be empty."
            )

        candidate = self._candidate_store.require_pending(
            candidate_id
        )

        rejected_candidate = replace(
            candidate,
            status=CandidateStatus.REJECTED,
            metadata={
                **candidate.metadata,
                "rejected_by": reviewer,
                "rejection_reason": explanation,
                "reviewed_at": utc_now_iso(),
            },
        )

        return self._candidate_store.replace(
            rejected_candidate
        )
