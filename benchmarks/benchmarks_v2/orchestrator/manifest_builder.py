from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .data_models import CampaignManifest
from .profiles import ProfileSpec


def _get_git_commit(repo_root: Path | None = None) -> str:
    """Return the current git commit hash, or a sentinel if not in a git repo."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


def _get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _compute_environment_hash(profile: ProfileSpec, families: List[str]) -> str:
    """Compute a deterministic hash of the benchmark environment."""
    env_data = {
        "python_version": _get_python_version(),
        "profile_name": profile.name,
        "profile_pairs": profile.total_pairs,
        "profile_seeds": sorted(profile.seeds),
        "families": sorted(families),
    }
    payload = json.dumps(env_data, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    *,
    profile: ProfileSpec,
    profile_name: str,
    families: List[str],
    repo_root: Path | None = None,
) -> CampaignManifest:
    """Build a new CampaignManifest from the given profile and families."""
    campaign_id = f"campaign-{uuid.uuid4().hex[:12]}"

    manifest = CampaignManifest(
        campaign_id=campaign_id,
        profile_name=profile_name,
        seeds=profile.seeds,
        total_pairs=profile.total_pairs * len(families),
        created_by="orchestrator",
    )

    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: CampaignManifest) -> None:
    """Validate a CampaignManifest for internal consistency."""
    errors: list[str] = []

    if not manifest.campaign_id:
        errors.append("campaign_id must not be empty")
    if not manifest.profile_name:
        errors.append("profile_name must not be empty")
    if not manifest.seeds:
        errors.append("seeds list must not be empty")
    if manifest.total_pairs < 0:
        errors.append(f"total_pairs must be non-negative, got {manifest.total_pairs}")

    if errors:
        raise ValueError("Manifest validation failed:\n  " + "\n  ".join(errors))


def save_manifest(manifest: CampaignManifest, output_dir: Path) -> Path:
    """Persist a manifest to disk and return the file path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"{manifest.campaign_id}_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as fh:
        fh.write(manifest.to_json(indent=2))

    return manifest_path


def load_manifest(manifest_path: Path) -> CampaignManifest:
    """Load a CampaignManifest from a JSON file."""
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return CampaignManifest.from_dict(data)
