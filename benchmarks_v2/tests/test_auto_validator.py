from __future__ import annotations

import pytest

from benchmarks_v2.orchestrator.auto_validator import AutoValidator


class TestExactMatchValidation:
    def test_exact_match_validation(self):
        """Exact match approves candidate."""
        validator = AutoValidator(threshold=0.8)
        candidate = "The Eiffel Tower is located in Paris, France."
        reference = "The Eiffel Tower is located in Paris, France."

        result = validator.validate(candidate, reference)
        assert result.approved is True
        assert result.similarity >= 0.99


class TestLowSimilarityRejection:
    def test_low_similarity_rejection(self):
        """Low similarity rejects candidate."""
        validator = AutoValidator(threshold=0.8)
        candidate = "Quantum computing uses qubits for computation."
        reference = "The Eiffel Tower is a wrought-iron lattice tower in Paris."

        result = validator.validate(candidate, reference)
        assert result.approved is False
        assert result.similarity < 0.8


class TestBatchValidation:
    def test_batch_validation(self):
        """Batch validation returns correct results."""
        validator = AutoValidator(threshold=0.8)
        candidates = [
            "Paris is the capital of France.",
            "The moon is made of cheese.",
            "Lyon is a city in France.",
        ]
        reference = "Paris is the capital of France."

        results = validator.validate_batch(candidates, reference)

        assert len(results) == 3
        assert results[0].approved is True
        assert results[1].approved is False
        assert hasattr(results[2], "approved")
        assert hasattr(results[2], "similarity")

    def test_batch_validation_empty(self):
        """Empty batch returns empty results."""
        validator = AutoValidator(threshold=0.8)
        results = validator.validate_batch([], "some reference")
        assert results == []
