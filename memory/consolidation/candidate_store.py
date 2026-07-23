"""Persistent lifecycle store for memoriX memory candidates."""

from __future__ import annotations

from pathlib import Path

from memory.data import CandidateStatus, MemoryCandidate
from memory.data.jsonl_store import (
    append_json_line,
    read_json_lines,
    rewrite_json_lines,
)
from memory.data.paths import DEFAULT_STORAGE_PATHS


class CandidateNotFoundError(LookupError):
    """Raised when a requested candidate does not exist."""


class CandidateAlreadyExistsError(ValueError):
    """Raised when a candidate identifier is already stored."""


class CandidateAlreadyProcessedError(ValueError):
    """Raised when a non-pending candidate is processed again."""


class MemoryCandidateStore:
    """JSONL-backed candidate repository with explicit lifecycle states."""

    def __init__(
        self,
        path: str | Path = DEFAULT_STORAGE_PATHS.memory_candidates,
    ) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Return the configured candidate file."""

        return self._path

    def list_candidates(
        self,
        *,
        status: CandidateStatus | None = None,
    ) -> tuple[MemoryCandidate, ...]:
        """List candidates, optionally filtered by lifecycle status."""

        candidates = tuple(
            MemoryCandidate.from_dict(payload)
            for payload in read_json_lines(self._path)
        )

        if status is None:
            return candidates

        expected_status = CandidateStatus(status)

        return tuple(
            candidate
            for candidate in candidates
            if candidate.status is expected_status
        )

    def get(self, candidate_id: str) -> MemoryCandidate:
        """Return one candidate or raise CandidateNotFoundError."""

        identifier = candidate_id.strip()

        for candidate in self.list_candidates():
            if candidate.candidate_id == identifier:
                return candidate

        raise CandidateNotFoundError(
            f"Candidate not found: {identifier}"
        )

    def add(self, candidate: MemoryCandidate) -> MemoryCandidate:
        """Persist a new pending candidate."""

        if not isinstance(candidate, MemoryCandidate):
            raise TypeError(
                "candidate must be a MemoryCandidate."
            )

        if candidate.status is not CandidateStatus.PENDING:
            raise ValueError(
                "A newly proposed candidate must be pending."
            )

        try:
            self.get(candidate.candidate_id)
        except CandidateNotFoundError:
            pass
        else:
            raise CandidateAlreadyExistsError(
                f"Candidate already exists: "
                f"{candidate.candidate_id}"
            )

        append_json_line(self._path, candidate.to_dict())
        return candidate

    def replace(
        self,
        candidate: MemoryCandidate,
    ) -> MemoryCandidate:
        """Replace an existing candidate while preserving file order."""

        if not isinstance(candidate, MemoryCandidate):
            raise TypeError(
                "candidate must be a MemoryCandidate."
            )

        candidates = list(self.list_candidates())
        replacement_index: int | None = None

        for index, stored_candidate in enumerate(candidates):
            if (
                stored_candidate.candidate_id
                == candidate.candidate_id
            ):
                replacement_index = index
                break

        if replacement_index is None:
            raise CandidateNotFoundError(
                f"Candidate not found: "
                f"{candidate.candidate_id}"
            )

        candidates[replacement_index] = candidate

        rewrite_json_lines(
            self._path,
            (
                stored_candidate.to_dict()
                for stored_candidate in candidates
            ),
        )

        return candidate

    def require_pending(
        self,
        candidate_id: str,
    ) -> MemoryCandidate:
        """Return a candidate only when it is still pending."""

        candidate = self.get(candidate_id)

        if candidate.status is not CandidateStatus.PENDING:
            raise CandidateAlreadyProcessedError(
                f"Candidate {candidate_id} is already "
                f"{candidate.status.value}."
            )

        return candidate
