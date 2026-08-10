from __future__ import annotations

import pytest

from benchmarks_v2.orchestrator.profiles import (
    ProfileName,
    ProfileSpec,
    load_profile,
    validate_profile,
)


class TestLoadSmokeProfile:
    def test_load_smoke_profile(self):
        """Smoke profile loads with correct values."""
        profile = load_profile("smoke")
        assert profile.name == "smoke"
        assert profile.total_pairs >= 1
        assert len(profile.seeds) >= 1
        assert profile.max_retries >= 0


class TestLoadPilotProfile:
    def test_load_pilot_profile(self):
        """Pilot profile loads with correct values."""
        profile = load_profile("pilot")
        assert profile.name == "pilot"
        assert profile.total_pairs >= 2
        assert len(profile.seeds) >= 2


class TestLoadStandardProfile:
    def test_load_standard_profile(self):
        """Standard profile loads with correct values."""
        profile = load_profile("standard")
        assert profile.name == "standard"
        assert profile.total_pairs >= 10
        assert len(profile.seeds) >= 3


class TestLoadLargeProfile:
    def test_load_large_profile(self):
        """Large profile loads with correct values."""
        profile = load_profile("large")
        assert profile.name == "large"
        assert profile.total_pairs >= 50
        assert len(profile.seeds) >= 5


class TestLoadResearchProfile:
    def test_load_research_profile(self):
        """Research profile loads with correct values."""
        profile = load_profile("research")
        assert profile.name == "research"
        assert profile.total_pairs >= 100
        assert len(profile.seeds) >= 10


class TestInvalidProfileRejected:
    def test_invalid_profile_rejected(self):
        """Invalid profile name raises ValueError."""
        with pytest.raises((ValueError, KeyError)):
            load_profile("nonexistent_profile_xyz")


class TestProfileValidationRejectsNegativePairs:
    def test_profile_validation_rejects_negative_pairs(self):
        """Negative pairs raises ValueError."""
        profile = ProfileSpec(
            name="invalid",
            total_pairs=-5,
            seeds=[1, 2, 3],
            max_retries=3,
            timeout_seconds=300,
        )
        with pytest.raises(ValueError):
            validate_profile(profile)


class TestProfileValidationRejectsEmptySeeds:
    def test_profile_validation_rejects_empty_seeds(self):
        """Empty seeds raises ValueError."""
        profile = ProfileSpec(
            name="invalid",
            total_pairs=10,
            seeds=[],
            max_retries=3,
            timeout_seconds=300,
        )
        with pytest.raises(ValueError):
            validate_profile(profile)
