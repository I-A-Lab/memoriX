from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of a single candidate validation."""
    candidate: str
    reference: str
    similarity: float
    approved: bool


class AutoValidator:
    """Validate candidate text against reference text using string similarity.

    Uses a character-level bigram similarity metric (no external dependencies).
    """

    def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = threshold

    def _bigrams(self, text: str) -> set:
        """Extract character bigrams from text."""
        normalized = text.lower().strip()
        if len(normalized) < 2:
            return {normalized}
        return {normalized[i:i + 2] for i in range(len(normalized) - 1)}

    def _similarity(self, a: str, b: str) -> float:
        """Compute bigram similarity between two strings."""
        if a == b:
            return 1.0
        if not a or not b:
            return 0.0

        bigrams_a = self._bigrams(a)
        bigrams_b = self._bigrams(b)

        if not bigrams_a or not bigrams_b:
            return 0.0

        intersection = bigrams_a & bigrams_b
        union = bigrams_a | bigrams_b

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def validate(self, candidate: str, reference: str) -> ValidationResult:
        """Validate a single candidate against a reference string."""
        similarity = self._similarity(candidate, reference)
        approved = similarity >= self.threshold

        return ValidationResult(
            candidate=candidate,
            reference=reference,
            similarity=round(similarity, 4),
            approved=approved,
        )

    def validate_batch(
        self, candidates: List[str], reference: str
    ) -> List[ValidationResult]:
        """Validate a batch of candidates against a reference string."""
        return [self.validate(c, reference) for c in candidates]
