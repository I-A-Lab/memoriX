from __future__ import annotations

import pytest

from benchmarks_v2.orchestrator.profiles import load_profile, validate_profile
from benchmarks_v2.orchestrator.data_models import CampaignManifest
from benchmarks_v2.orchestrator.orchestrator import BenchmarkOrchestrator


class TestSmokeProfileLoads:
    def test_smoke_profile_loads(self):
        """Smoke profile loads and validates."""
        profile = load_profile("smoke")
        validate_profile(profile)
        assert profile.name == "smoke"
        assert profile.total_pairs >= 1


class TestManifestBuilderCreatesManifest:
    def test_manifest_builder_creates_manifest(self):
        """Manifest is created with valid fields."""
        manifest = CampaignManifest(
            campaign_id="test-campaign-001",
            profile_name="smoke",
            seeds=[42],
            total_pairs=1,
            created_by="test_integration",
        )
        assert manifest.campaign_id == "test-campaign-001"
        assert manifest.profile_name == "smoke"
        assert manifest.seeds == [42]
        assert manifest.total_pairs == 1
        assert manifest.created_by == "test_integration"

    def test_manifest_serialization_roundtrip(self):
        """Manifest can be serialized and deserialized."""
        manifest = CampaignManifest(
            campaign_id="test-campaign-002",
            profile_name="pilot",
            seeds=[1, 2, 3],
            total_pairs=3,
            created_by="test_integration",
        )
        data = manifest.to_dict()
        restored = CampaignManifest.from_dict(data)
        assert restored.campaign_id == manifest.campaign_id
        assert restored.profile_name == manifest.profile_name
        assert restored.seeds == manifest.seeds
        assert restored.total_pairs == manifest.total_pairs


class TestOrchestratorDryRun:
    def test_orchestrator_dry_run(self, tmp_path):
        """Dry run produces no side effects."""
        orchestrator = BenchmarkOrchestrator(
            output_dir=tmp_path,
            dry_run=True,
        )
        manifest = CampaignManifest(
            campaign_id="dry-run-test",
            profile_name="smoke",
            seeds=[42],
            total_pairs=1,
            created_by="test_integration",
        )

        results = orchestrator.run(manifest, families=["f01_exact_key_recall"])

        output_files = list(tmp_path.rglob("raw_results.json"))
        assert len(output_files) == 1
        assert len(results) == 2  # 1 seed x 2 modes
        for r in results:
            assert r.dry_run is True
