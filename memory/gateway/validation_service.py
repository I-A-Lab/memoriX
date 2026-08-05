"""Human candidate-review gateway for the Titan hot site."""

from __future__ import annotations

from memory.gateway.adaptive_validation import (
    AdaptiveValidationMetadataService,
)
from memory.gateway.capacity_control import (
    require_capacity_admission,
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
        *,
        configured_capacity: int = 50_000,
    ) -> None:
        if configured_capacity <= 0:
            raise ValueError("configured_capacity must be positive.")

        self._candidate_store = candidate_store
        self._hot_site = hot_site
        self._configured_capacity = configured_capacity

    def validate(
        self,
        candidate_id: str,
        *,
        validated_by: str,
        validation_reason: str,
        final_content: str | None = None,
        supersedes_memory_id: str | None = None,
    ) -> ValidatedMemory:
        """Validate one pending candidate and store it in Titan only.

        The optional supersedes_memory_id is authoritative when
        provided: it selects the exact active hot-site memory that the
        validated replacement supersedes, independent of the candidate
        target_memory_id.
        """

        reviewer = validated_by.strip()
        explanation = validation_reason.strip()

        if not reviewer:
            raise ValueError("validated_by must not be empty.")

        if not explanation:
            raise ValueError(
                "validation_reason must not be empty."
            )

        explicit_target = (
            supersedes_memory_id.strip()
            if supersedes_memory_id is not None
            else None
        )

        if (
            supersedes_memory_id is not None
            and not explicit_target
        ):
            raise ValueError(
                "supersedes_memory_id must not be empty "
                "when provided."
            )

        candidate = self._candidate_store.require_pending(
            candidate_id
        )

        if (
            explicit_target is not None
            and candidate.target_memory_id is not None
            and explicit_target
            != candidate.target_memory_id
        ):
            raise ValueError(
                "supersedes_memory_id conflicts with the "
                "candidate target_memory_id."
            )

        resolved_target = (
            explicit_target or candidate.target_memory_id
        )

        require_capacity_admission(
            self._hot_site,
            configured_capacity=self._configured_capacity,
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

        if resolved_target is not None:
            existing = {
                memory.memory_id: memory
                for memory in self._hot_site.list_memories()
            }
            superseded_memory = existing.get(
                resolved_target
            )

            if superseded_memory is None:
                raise CandidateValidationError(
                    "The candidate targets an unknown hot-site "
                    f"memory: {resolved_target}"
                )

            if not superseded_memory.active:
                raise CandidateValidationError(
                    "The candidate targets an inactive hot-site "
                    f"memory: {resolved_target}"
                )

            if (
                superseded_memory.source_candidate_id
                == candidate.candidate_id
            ):
                raise CandidateValidationError(
                    "A candidate cannot supersede the memory "
                    "created from itself."
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
            target_action, target_error = self._soft_deactivate(
                superseded_memory.memory_id,
                validated_by=reviewer,
                reason=(
                    "Superseded by validated memory "
                    f"{validated_memory.memory_id}."
                ),
            )

            if target_action is not ForgetAction.DEACTIVATED:
                replacement_action, replacement_error = (
                    self._soft_deactivate(
                        validated_memory.memory_id,
                        validated_by=reviewer,
                        reason=(
                            "Compensation: the supersession "
                            f"target {superseded_memory.memory_id} "
                            "could not be deactivated."
                        ),
                    )
                )

                if (
                    replacement_action
                    is ForgetAction.DEACTIVATED
                ):
                    raise CandidateValidationError(
                        self._deactivation_failure_message(
                            validated_memory.memory_id,
                            superseded_memory.memory_id,
                            target_error,
                        )
                    )

                raise CandidateValidationError(
                    self._compensation_failure_message(
                        validated_memory.memory_id,
                        superseded_memory.memory_id,
                        target_error,
                        replacement_error,
                    )
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

    def _soft_deactivate(
        self,
        memory_id: str,
        *,
        validated_by: str,
        reason: str,
    ) -> tuple[ForgetAction, Exception | None]:
        """Deactivate one hot-site memory through the hot-site API.

        Returns (action, error): the ForgetAction reported by the
        hot site, and the raised exception when soft_forget did not
        return a result. Any action other than DEACTIVATED must be
        treated by the caller as a failure.
        """

        try:
            result = self._hot_site.soft_forget(
                memory_id,
                validated_by=validated_by,
                reason=reason,
            )
        except Exception as error:
            return ForgetAction.NOT_FOUND, error

        return result.action, None

    @staticmethod
    def _deactivation_failure_message(
        replacement_id: str,
        target_id: str,
        target_error: Exception | None,
    ) -> str:
        detail = (
            f"{type(target_error).__name__}: {target_error}"
            if target_error is not None
            else "no deactivated outcome was reported"
        )

        return (
            "The replacement memory was stored, but the "
            "superseded hot-site memory could not be deactivated"
            f" ({detail}). The replacement memory was "
            "soft-deactivated in compensation and the candidate "
            "remains pending. "
            f"Replacement memory_id: {replacement_id}; "
            f"target memory_id: {target_id}."
        )

    @staticmethod
    def _compensation_failure_message(
        replacement_id: str,
        target_id: str,
        target_error: Exception | None,
        replacement_error: Exception | None,
    ) -> str:
        target_detail = (
            f"{type(target_error).__name__}: {target_error}"
            if target_error is not None
            else "no deactivated outcome was reported"
        )
        replacement_detail = (
            f"{type(replacement_error).__name__}: "
            f"{replacement_error}"
            if replacement_error is not None
            else "no deactivated outcome was reported"
        )

        return (
            "The replacement memory was stored, but the superseded "
            "hot-site memory could not be deactivated"
            f" ({target_detail}), and the compensating "
            "soft-deactivation of the replacement also failed"
            f" ({replacement_detail}). The candidate remains "
            "pending. "
            f"Replacement memory_id: {replacement_id}; "
            f"target memory_id: {target_id}."
        )

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
