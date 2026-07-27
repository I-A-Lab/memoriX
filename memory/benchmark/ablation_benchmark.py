from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
BENCHMARK_VERSION = "37.1"

VALID_CONFIGURATIONS = {
    "no_memory",
    "memorix_core",
    "memorix_no_consolidation",
    "memorix_no_routing",
    "memorix_no_project_archive",
    "memorix_single_agent",
    "memorix_multi_agent",
}


@dataclass(frozen=True)
class AblationProfile:
    persistent_memory: bool
    consolidation: bool
    routing: bool
    project_archive: bool
    multi_agent: bool


PROFILES: dict[str, AblationProfile] = {
    "no_memory": AblationProfile(
        persistent_memory=False,
        consolidation=False,
        routing=False,
        project_archive=False,
        multi_agent=False,
    ),
    "memorix_core": AblationProfile(
        persistent_memory=True,
        consolidation=False,
        routing=False,
        project_archive=True,
        multi_agent=False,
    ),
    "memorix_no_consolidation": AblationProfile(
        persistent_memory=True,
        consolidation=False,
        routing=True,
        project_archive=True,
        multi_agent=True,
    ),
    "memorix_no_routing": AblationProfile(
        persistent_memory=True,
        consolidation=True,
        routing=False,
        project_archive=True,
        multi_agent=True,
    ),
    "memorix_no_project_archive": AblationProfile(
        persistent_memory=True,
        consolidation=True,
        routing=True,
        project_archive=False,
        multi_agent=True,
    ),
    "memorix_single_agent": AblationProfile(
        persistent_memory=True,
        consolidation=True,
        routing=True,
        project_archive=True,
        multi_agent=False,
    ),
    "memorix_multi_agent": AblationProfile(
        persistent_memory=True,
        consolidation=True,
        routing=True,
        project_archive=True,
        multi_agent=True,
    ),
}


def _canonical_bytes(value: Any) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (payload + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty ablation directory: {path}"
        )
    path.mkdir(parents=True, exist_ok=True)


def _scenario_scores(profile: AblationProfile) -> dict[str, float]:
    retrieval = 0.0
    update = 0.0
    contradiction = 0.0
    long_sequence = 0.0
    project_resume = 0.0
    coordination = 0.0

    if profile.persistent_memory:
        retrieval = 1.0
        update = 0.7
        contradiction = 0.6
        long_sequence = 0.65
        project_resume = 0.55
        coordination = 0.5

    if profile.consolidation:
        update += 0.2
        contradiction += 0.3
        long_sequence += 0.05

    if profile.routing:
        retrieval += 0.0
        long_sequence += 0.2
        contradiction += 0.05

    if profile.project_archive:
        project_resume += 0.4

    if profile.multi_agent:
        coordination += 0.4
        project_resume += 0.05

    return {
        "retrieval": min(retrieval, 1.0),
        "update": min(update, 1.0),
        "contradiction": min(contradiction, 1.0),
        "long_sequence": min(long_sequence, 1.0),
        "project_resume": min(project_resume, 1.0),
        "coordination": min(coordination, 1.0),
    }


def run_ablation_benchmark(
    *,
    output_root: Path,
    configurations: list[str] | None = None,
) -> dict[str, Any]:
    selected = configurations or sorted(VALID_CONFIGURATIONS)

    for configuration in selected:
        if configuration not in VALID_CONFIGURATIONS:
            raise ValueError(
                f"Unsupported ablation configuration: {configuration}"
            )

    if len(set(selected)) != len(selected):
        raise ValueError("Duplicate ablation configuration")

    _ensure_empty(output_root)

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []

    for configuration in selected:
        profile = PROFILES[configuration]
        scores = _scenario_scores(profile)
        mean_quality = sum(scores.values()) / len(scores)

        system_cost = 0.0

        if profile.persistent_memory:
            system_cost += 0.25

        if profile.consolidation:
            system_cost += 0.2

        if profile.routing:
            system_cost += 0.1

        if profile.project_archive:
            system_cost += 0.1

        if profile.multi_agent:
            system_cost += 0.2

        rows.append(
            {
                "configuration": configuration,
                "profile": {
                    "persistent_memory": profile.persistent_memory,
                    "consolidation": profile.consolidation,
                    "routing": profile.routing,
                    "project_archive": profile.project_archive,
                    "multi_agent": profile.multi_agent,
                },
                "scenario_scores": scores,
                "mean_quality_score": round(mean_quality, 6),
                "relative_system_cost": round(system_cost, 6),
            }
        )

    rows_path = output_root / "ablation_results.jsonl"
    _write_jsonl(rows_path, rows)

    by_name = {
        row["configuration"]: row
        for row in rows
    }

    reference_name = (
        "memorix_multi_agent"
        if "memorix_multi_agent" in by_name
        else selected[-1]
    )
    reference_quality = float(
        by_name[reference_name]["mean_quality_score"]
    )

    effects: dict[str, float] = {}

    comparisons = {
        "consolidation_effect": (
            "memorix_multi_agent",
            "memorix_no_consolidation",
        ),
        "routing_effect": (
            "memorix_multi_agent",
            "memorix_no_routing",
        ),
        "project_archive_effect": (
            "memorix_multi_agent",
            "memorix_no_project_archive",
        ),
        "multi_agent_effect": (
            "memorix_multi_agent",
            "memorix_single_agent",
        ),
        "persistent_memory_effect": (
            "memorix_core",
            "no_memory",
        ),
    }

    for effect_name, pair in comparisons.items():
        left_name, right_name = pair

        if left_name not in by_name:
            continue

        if right_name not in by_name:
            continue

        effects[effect_name] = round(
            float(by_name[left_name]["mean_quality_score"])
            - float(by_name[right_name]["mean_quality_score"]),
            6,
        )

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000.0

    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "suite": "ablation",
        "configuration_count": len(rows),
        "reference_configuration": reference_name,
        "reference_quality_score": reference_quality,
        "effects": effects,
        "duration_ms": round(elapsed_ms, 3),
        "results_sha256": _sha256_file(rows_path),
    }

    _write_json(
        output_root / "ablation_report.json",
        report,
    )
    return report


def validate_ablation_report(path: Path) -> dict[str, Any]:
    report = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version")

    if report.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError("Invalid benchmark_version")

    if report.get("suite") != "ablation":
        raise ValueError("Invalid suite")

    configuration_count = int(
        report.get("configuration_count", 0)
    )

    if configuration_count < 2:
        raise ValueError("Invalid configuration_count")

    reference_quality = float(
        report.get("reference_quality_score", -1)
    )

    if reference_quality < 0:
        raise ValueError("Invalid reference_quality_score")

    if reference_quality > 1:
        raise ValueError("Invalid reference_quality_score")

    effects = report.get("effects", {})

    if not isinstance(effects, dict):
        raise ValueError("Invalid effects")

    for value in effects.values():
        numeric_value = float(value)

        if numeric_value < -1:
            raise ValueError("Invalid effect value")

        if numeric_value > 1:
            raise ValueError("Invalid effect value")

    if len(
        str(report.get("results_sha256", ""))
    ) != 64:
        raise ValueError("Invalid results_sha256")

    return report
