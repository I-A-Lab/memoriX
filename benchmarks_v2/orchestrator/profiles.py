from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ProfileName(str, Enum):
    smoke = "smoke"
    pilot = "pilot"
    standard = "standard"
    large = "large"
    research = "research"


@dataclass(frozen=True, slots=True)
class ProfileSpec:
    name: str
    total_pairs: int
    seeds: List[int] = field(repr=True)
    max_retries: int = 0
    timeout_seconds: int = 300

    @property
    def total_runs(self) -> int:
        return self.total_pairs * len(self.seeds)


def load_profile(name: str, config_dir: Path | None = None) -> ProfileSpec:
    """Load a benchmark profile by name from the profiles.json config."""
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent / "configs"
    config_path = config_dir / "profiles.json"

    if not config_path.exists():
        raise FileNotFoundError(f"Profiles config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if data.get("schema_version") != 1:
        raise ValueError(f"Unsupported profiles schema version: {data.get('schema_version')}")

    profiles = data.get("profiles", {})
    raw = profiles.get(name)
    if raw is None:
        available = ", ".join(sorted(profiles.keys()))
        raise ValueError(f"Unknown profile '{name}'. Available: {available}")

    return ProfileSpec(
        name=name,
        total_pairs=raw["pairs"],
        seeds=list(raw["seeds"]),
        max_retries=raw.get("max_retries", 0),
        timeout_seconds=raw["timeout_seconds"],
    )


def validate_profile(spec: ProfileSpec) -> None:
    """Validate a ProfileSpec for internal consistency."""
    errors: list[str] = []

    if spec.total_pairs <= 0:
        errors.append(f"total_pairs must be positive, got {spec.total_pairs}")
    if not spec.seeds:
        errors.append("seeds must not be empty")
    if any(s < 0 for s in spec.seeds):
        errors.append("all seeds must be non-negative")
    if spec.max_retries < 0:
        errors.append(f"max_retries must be non-negative, got {spec.max_retries}")
    if spec.timeout_seconds <= 0:
        errors.append(f"timeout_seconds must be positive, got {spec.timeout_seconds}")

    if errors:
        raise ValueError("Profile validation failed:\n  " + "\n  ".join(errors))


def list_profiles(config_dir: Path | None = None) -> list[str]:
    """Return all available profile names."""
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent / "configs"
    config_path = config_dir / "profiles.json"

    with open(config_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    return sorted(data.get("profiles", {}).keys())
