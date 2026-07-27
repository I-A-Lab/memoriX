"""Stable contracts for the memoriX versus no-memory benchmark."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence


BENCHMARK_ID = "memorix_vs_no_memory"
SCHEMA_VERSION = 1


class BenchmarkMode(str, Enum):
    """Official configurations introduced by the global benchmark."""

    NO_MEMORY = "no_memory"
    MEMORIX_CORE = "memorix_core"
    MEMORIX_FULL = "memorix_full"


class BenchmarkSuite(str, Enum):
    """Families of experiments kept separate in reports."""

    MEMORY = "memory"
    AGENT = "agent"
    SDLC = "sdlc"
    SYSTEM = "system"
    ROBUSTNESS = "robustness"


class BenchmarkSize(str, Enum):
    """Bounded benchmark volume profiles."""

    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    STRESS = "stress"
    EXTREME = "extreme"


@dataclass(frozen=True, slots=True)
class ModeContract:
    """Feature contract for one benchmark mode."""

    mode: BenchmarkMode
    persistent_memory: bool
    memory_tools_exposed: bool
    memorix_plugin_loaded: bool
    memorix_prompts_enabled: bool
    mcp_server_allowed: bool
    runtime_creation_allowed: bool
    titan_enabled: bool
    cold_site_enabled: bool
    candidates_enabled: bool
    consolidation_enabled: bool
    adaptive_routing_enabled: bool
    active_policy_enabled: bool
    project_archive_enabled: bool

    def validate(self) -> None:
        if self.mode is BenchmarkMode.NO_MEMORY:
            forbidden = {
                "persistent_memory": self.persistent_memory,
                "memory_tools_exposed": self.memory_tools_exposed,
                "memorix_plugin_loaded": self.memorix_plugin_loaded,
                "memorix_prompts_enabled": self.memorix_prompts_enabled,
                "mcp_server_allowed": self.mcp_server_allowed,
                "runtime_creation_allowed": self.runtime_creation_allowed,
                "titan_enabled": self.titan_enabled,
                "cold_site_enabled": self.cold_site_enabled,
                "candidates_enabled": self.candidates_enabled,
                "consolidation_enabled": self.consolidation_enabled,
                "adaptive_routing_enabled": self.adaptive_routing_enabled,
                "active_policy_enabled": self.active_policy_enabled,
                "project_archive_enabled": self.project_archive_enabled,
            }
            enabled = sorted(name for name, value in forbidden.items() if value)
            if enabled:
                raise ValueError(
                    "no_memory enables forbidden features: " + ", ".join(enabled)
                )

        if self.mode is BenchmarkMode.MEMORIX_CORE:
            required = {
                "persistent_memory": self.persistent_memory,
                "memory_tools_exposed": self.memory_tools_exposed,
                "memorix_prompts_enabled": self.memorix_prompts_enabled,
                "mcp_server_allowed": self.mcp_server_allowed,
                "runtime_creation_allowed": self.runtime_creation_allowed,
                "titan_enabled": self.titan_enabled,
                "cold_site_enabled": self.cold_site_enabled,
                "candidates_enabled": self.candidates_enabled,
                "project_archive_enabled": self.project_archive_enabled,
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise ValueError(
                    "memorix_core is missing required features: " + ", ".join(missing)
                )
            if self.consolidation_enabled:
                raise ValueError("memorix_core must keep consolidation disabled.")
            if self.adaptive_routing_enabled:
                raise ValueError("memorix_core must keep adaptive routing disabled.")
            if self.active_policy_enabled:
                raise ValueError("memorix_core must keep active policies disabled.")

        if self.mode is BenchmarkMode.MEMORIX_FULL:
            required = {
                field_name: bool(getattr(self, field_name))
                for field_name in (
                    "persistent_memory",
                    "memory_tools_exposed",
                    "memorix_plugin_loaded",
                    "memorix_prompts_enabled",
                    "mcp_server_allowed",
                    "runtime_creation_allowed",
                    "titan_enabled",
                    "cold_site_enabled",
                    "candidates_enabled",
                    "consolidation_enabled",
                    "adaptive_routing_enabled",
                    "active_policy_enabled",
                    "project_archive_enabled",
                )
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise ValueError(
                    "memorix_full is missing required features: " + ", ".join(missing)
                )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        return payload


@dataclass(frozen=True, slots=True)
class FairnessContract:
    """Variables that must remain equal within one paired comparison."""

    paired_fields: tuple[str, ...]
    alternating_order: bool
    isolated_runtime_per_run: bool
    fixed_seeds: bool
    raw_results_immutable: bool
    failed_runs_retained: bool

    def validate(self) -> None:
        required = {
            "git_commit",
            "task_id",
            "dataset_id",
            "prompt_version",
            "model_id",
            "model_parameters",
            "tool_budget",
            "turn_budget",
            "timeout_seconds",
            "hardware_id",
            "seed",
            "evaluator_version",
        }
        missing = sorted(required.difference(self.paired_fields))
        if missing:
            raise ValueError(
                "Fairness contract is missing paired fields: " + ", ".join(missing)
            )
        if not self.alternating_order:
            raise ValueError("Paired execution order must alternate.")
        if not self.isolated_runtime_per_run:
            raise ValueError("Each run must use an isolated runtime.")
        if not self.fixed_seeds:
            raise ValueError("Benchmark seeds must be fixed and recorded.")
        if not self.raw_results_immutable:
            raise ValueError("Raw benchmark results must be immutable.")
        if not self.failed_runs_retained:
            raise ValueError("Failed runs must be retained in raw results.")


@dataclass(frozen=True, slots=True)
class SizeContract:
    """One bounded benchmark volume profile."""

    size: BenchmarkSize
    memory_count: int
    distractor_count: int
    default_seed_count: int
    automatic: bool

    def validate(self) -> None:
        if self.memory_count < 0:
            raise ValueError("memory_count must be non-negative.")
        if self.distractor_count < 0:
            raise ValueError("distractor_count must be non-negative.")
        if self.default_seed_count <= 0:
            raise ValueError("default_seed_count must be positive.")
        if self.size is BenchmarkSize.EXTREME and self.automatic:
            raise ValueError("The extreme profile must never run automatically.")


@dataclass(frozen=True, slots=True)
class BenchmarkContracts:
    """Validated top-level contracts loaded from versioned JSON files."""

    modes: tuple[ModeContract, ...]
    fairness: FairnessContract
    sizes: tuple[SizeContract, ...]
    primary_metrics: Mapping[str, tuple[str, ...]]
    schema_version: int = SCHEMA_VERSION

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported schema_version={self.schema_version}; "
                f"expected {SCHEMA_VERSION}."
            )

        expected_modes = set(BenchmarkMode)
        actual_modes = {item.mode for item in self.modes}
        if actual_modes != expected_modes:
            missing = sorted(mode.value for mode in expected_modes - actual_modes)
            extra = sorted(mode.value for mode in actual_modes - expected_modes)
            raise ValueError(
                f"Invalid mode set; missing={missing}, extra={extra}."
            )
        if len(self.modes) != len(actual_modes):
            raise ValueError("Duplicate benchmark modes are not allowed.")

        expected_sizes = set(BenchmarkSize)
        actual_sizes = {item.size for item in self.sizes}
        if actual_sizes != expected_sizes:
            missing = sorted(size.value for size in expected_sizes - actual_sizes)
            extra = sorted(size.value for size in actual_sizes - expected_sizes)
            raise ValueError(
                f"Invalid size set; missing={missing}, extra={extra}."
            )
        if len(self.sizes) != len(actual_sizes):
            raise ValueError("Duplicate benchmark sizes are not allowed.")

        for mode in self.modes:
            mode.validate()
        self.fairness.validate()
        for size in self.sizes:
            size.validate()

        required_metric_groups = {suite.value for suite in BenchmarkSuite}
        missing_metric_groups = sorted(
            required_metric_groups.difference(self.primary_metrics)
        )
        if missing_metric_groups:
            raise ValueError(
                "Missing primary metric groups: " + ", ".join(missing_metric_groups)
            )
        for group, names in self.primary_metrics.items():
            if not names:
                raise ValueError(f"Metric group {group!r} must not be empty.")
            if len(names) != len(set(names)):
                raise ValueError(f"Metric group {group!r} contains duplicates.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": BENCHMARK_ID,
            "schema_version": self.schema_version,
            "modes": [item.to_dict() for item in self.modes],
            "fairness": asdict(self.fairness),
            "sizes": [
                {
                    **asdict(item),
                    "size": item.size.value,
                }
                for item in self.sizes
            ],
            "primary_metrics": {
                group: list(names)
                for group, names in self.primary_metrics.items()
            },
        }


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object.")
    return value


def _require_sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a JSON array.")
    return value


def load_benchmark_contracts(config_root: Path) -> BenchmarkContracts:
    """Load and validate the versioned Part 29 benchmark contracts."""

    config_root = Path(config_root)
    configurations_payload = json.loads(
        (config_root / "configurations.json").read_text(encoding="utf-8")
    )
    metrics_payload = json.loads(
        (config_root / "metrics.json").read_text(encoding="utf-8")
    )
    sizes_payload = json.loads(
        (config_root / "sizes.json").read_text(encoding="utf-8")
    )

    configurations = _require_mapping(
        configurations_payload,
        "configurations.json",
    )
    metrics = _require_mapping(metrics_payload, "metrics.json")
    sizes = _require_mapping(sizes_payload, "sizes.json")

    schema_versions = {
        int(configurations.get("schema_version", -1)),
        int(metrics.get("schema_version", -1)),
        int(sizes.get("schema_version", -1)),
    }
    if schema_versions != {SCHEMA_VERSION}:
        raise ValueError(
            "All benchmark configuration files must use schema_version=1."
        )

    raw_modes = _require_sequence(configurations.get("modes"), "modes")
    modes = tuple(
        ModeContract(
            mode=BenchmarkMode(str(_require_mapping(raw, "mode")["mode"])),
            **{
                field_name: bool(_require_mapping(raw, "mode")[field_name])
                for field_name in (
                    "persistent_memory",
                    "memory_tools_exposed",
                    "memorix_plugin_loaded",
                    "memorix_prompts_enabled",
                    "mcp_server_allowed",
                    "runtime_creation_allowed",
                    "titan_enabled",
                    "cold_site_enabled",
                    "candidates_enabled",
                    "consolidation_enabled",
                    "adaptive_routing_enabled",
                    "active_policy_enabled",
                    "project_archive_enabled",
                )
            },
        )
        for raw in raw_modes
    )

    fairness_raw = _require_mapping(configurations.get("fairness"), "fairness")
    fairness = FairnessContract(
        paired_fields=tuple(
            str(item)
            for item in _require_sequence(
                fairness_raw.get("paired_fields"),
                "fairness.paired_fields",
            )
        ),
        alternating_order=bool(fairness_raw.get("alternating_order")),
        isolated_runtime_per_run=bool(
            fairness_raw.get("isolated_runtime_per_run")
        ),
        fixed_seeds=bool(fairness_raw.get("fixed_seeds")),
        raw_results_immutable=bool(
            fairness_raw.get("raw_results_immutable")
        ),
        failed_runs_retained=bool(fairness_raw.get("failed_runs_retained")),
    )

    raw_sizes = _require_sequence(sizes.get("sizes"), "sizes")
    size_contracts = tuple(
        SizeContract(
            size=BenchmarkSize(str(_require_mapping(raw, "size")["size"])),
            memory_count=int(_require_mapping(raw, "size")["memory_count"]),
            distractor_count=int(
                _require_mapping(raw, "size")["distractor_count"]
            ),
            default_seed_count=int(
                _require_mapping(raw, "size")["default_seed_count"]
            ),
            automatic=bool(_require_mapping(raw, "size")["automatic"]),
        )
        for raw in raw_sizes
    )

    primary_metrics_raw = _require_mapping(
        metrics.get("primary_metrics"),
        "primary_metrics",
    )
    primary_metrics = {
        str(group): tuple(
            str(item)
            for item in _require_sequence(names, f"primary_metrics.{group}")
        )
        for group, names in primary_metrics_raw.items()
    }

    contracts = BenchmarkContracts(
        modes=modes,
        fairness=fairness,
        sizes=size_contracts,
        primary_metrics=primary_metrics,
    )
    contracts.validate()
    return contracts
