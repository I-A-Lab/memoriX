from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
BENCHMARK_VERSION = "36.1"
VALID_MODES = {"no_memory", "memorix_core"}
VALID_BACKENDS = {"deterministic"}


def _canonical_bytes(value: Any) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return (payload + "\n").encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ensure_empty(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty directory: {path}"
        )
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))


def _run_tests(project_root: Path) -> tuple[bool, str, float]:
    started = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    output = (process.stdout or "") + (process.stderr or "")
    return process.returncode == 0, output, elapsed_ms


def _write_initial_project(project_root: Path, mode: str) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "tests").mkdir(parents=True, exist_ok=True)

    source = """from __future__ import annotations

import secrets
import string


def generate_password(
    length: int,
    include_symbols: bool = True,
) -> str:
    if length < 8:
        raise ValueError("length must be at least 8")

    alphabet = string.ascii_letters + string.digits

    if include_symbols:
        alphabet += "!@#$%^&*"

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )
"""

    tests = """import unittest

from password_generator import generate_password


class PasswordGeneratorTests(unittest.TestCase):
    def test_length(self):
        self.assertEqual(len(generate_password(16)), 16)

    def test_minimum_length(self):
        with self.assertRaises(ValueError):
            generate_password(7)

    def test_without_symbols(self):
        value = generate_password(20, include_symbols=False)
        self.assertTrue(value.isalnum())


if __name__ == "__main__":
    unittest.main()
"""

    (project_root / "password_generator.py").write_text(
        source,
        encoding="utf-8",
        newline="\n",
    )
    (project_root / "tests" / "test_password_generator.py").write_text(
        tests,
        encoding="utf-8",
        newline="\n",
    )
    (project_root / "README.md").write_text(
        "# Password Generator\n",
        encoding="utf-8",
        newline="\n",
    )

    if mode == "memorix_core":
        decisions = [
            {
                "decision_id": "language",
                "value": "python",
            },
            {
                "decision_id": "api",
                "value": (
                    "generate_password("
                    "length, include_symbols=True"
                    ")"
                ),
            },
            {
                "decision_id": "security",
                "value": "use secrets instead of random",
            },
        ]
        _write_json(
            project_root / ".memorix_decisions.json",
            decisions,
        )


def _apply_second_session_change(
    project_root: Path,
    mode: str,
) -> bool:
    recovered_decisions: list[dict[str, Any]] = []
    decisions_path = project_root / ".memorix_decisions.json"

    if mode == "memorix_core" and decisions_path.is_file():
        recovered_decisions = json.loads(
            decisions_path.read_text(encoding="utf-8-sig")
        )

    security_decision_reused = any(
        item.get("decision_id") == "security"
        and item.get("value") == "use secrets instead of random"
        for item in recovered_decisions
    )

    source_path = project_root / "password_generator.py"
    source = source_path.read_text(encoding="utf-8")

    if security_decision_reused:
        source = source.replace(
            "    include_symbols: bool = True,\n"
            ") -> str:",
            "    include_symbols: bool = True,\n"
            "    prefix: str = \"\",\n"
            ") -> str:",
            1,
        )
        source = source.replace(
            "    return \"\".join(\n"
            "        secrets.choice(alphabet)\n"
            "        for _ in range(length)\n"
            "    )",
            "    generated = \"\".join(\n"
            "        secrets.choice(alphabet)\n"
            "        for _ in range(length)\n"
            "    )\n"
            "    return prefix + generated",
            1,
        )
    else:
        source = source.replace(
            "import secrets",
            "import random",
            1,
        )
        source = source.replace(
            "secrets.choice",
            "random.choice",
        )

    source_path.write_text(
        source,
        encoding="utf-8",
        newline="\n",
    )

    evolution_tests = """import unittest

import password_generator
from password_generator import generate_password


class EvolutionTests(unittest.TestCase):
    def test_prefix(self):
        value = generate_password(12, prefix="APP-")
        self.assertTrue(value.startswith("APP-"))

    def test_secure_generator_is_preserved(self):
        self.assertTrue(hasattr(password_generator, "secrets"))
        self.assertFalse(hasattr(password_generator, "random"))


if __name__ == "__main__":
    unittest.main()
"""

    (
        project_root
        / "tests"
        / "test_evolution.py"
    ).write_text(
        evolution_tests,
        encoding="utf-8",
        newline="\n",
    )

    return security_decision_reused


def run_sdlc_benchmark(
    *,
    output_root: Path,
    mode: str,
    backend: str = "deterministic",
) -> dict[str, Any]:
    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported mode: {mode}")

    if backend not in VALID_BACKENDS:
        raise ValueError(f"Unsupported backend: {backend}")

    _ensure_empty(output_root)

    workspace = output_root / "workspace"
    started = time.perf_counter()
    episodes: list[dict[str, Any]] = []

    _write_initial_project(workspace, mode)

    initial_success, initial_output, initial_ms = _run_tests(
        workspace
    )
    episodes.append(
        {
            "episode": 1,
            "name": "initial_creation",
            "success": initial_success,
            "decision_reused": False,
            "test_duration_ms": round(initial_ms, 3),
            "test_output": initial_output[-2000:],
        }
    )

    decision_reused = _apply_second_session_change(
        workspace,
        mode,
    )

    second_success, second_output, second_ms = _run_tests(
        workspace
    )
    episodes.append(
        {
            "episode": 2,
            "name": "new_session_requirement_change",
            "success": second_success,
            "decision_reused": decision_reused,
            "test_duration_ms": round(second_ms, 3),
            "test_output": second_output[-2000:],
        }
    )

    total_ms = (
        time.perf_counter() - started
    ) * 1000.0

    successful_episodes = sum(
        1 for episode in episodes if episode["success"]
    )

    episodes_path = (
        output_root / "sdlc_episode_results.jsonl"
    )
    _write_jsonl(episodes_path, episodes)

    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_version": BENCHMARK_VERSION,
        "benchmark_id": "memorix_vs_no_memory",
        "suite": "sdlc",
        "mode": mode,
        "backend": backend,
        "metrics": {
            "episode_count": len(episodes),
            "task_completion_rate": (
                successful_episodes / len(episodes)
            ),
            "test_pass_rate": (
                successful_episodes / len(episodes)
            ),
            "decision_reuse_accuracy": (
                1.0 if decision_reused else 0.0
            ),
            "regression_count": (
                0 if second_success else 1
            ),
            "session_resume_success_rate": (
                1.0 if second_success else 0.0
            ),
            "total_duration_ms": round(
                total_ms,
                3,
            ),
        },
        "episodes_sha256": _sha256_file(
            episodes_path
        ),
    }

    _write_json(
        output_root / "sdlc_report.json",
        report,
    )

    return report


def validate_sdlc_report(
    path: Path,
) -> dict[str, Any]:
    report = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Invalid schema_version")

    if report.get("benchmark_version") != BENCHMARK_VERSION:
        raise ValueError("Invalid benchmark_version")

    if report.get("mode") not in VALID_MODES:
        raise ValueError("Invalid mode")

    if report.get("backend") not in VALID_BACKENDS:
        raise ValueError("Invalid backend")

    metrics = report.get("metrics", {})

    bounded_metrics = (
        "task_completion_rate",
        "test_pass_rate",
        "decision_reuse_accuracy",
        "session_resume_success_rate",
    )

    for metric_name in bounded_metrics:
        metric_value = float(
            metrics.get(metric_name, -1)
        )

        if metric_value < 0:
            raise ValueError(
                f"Invalid metric: {metric_name}"
            )

        if metric_value > 1:
            raise ValueError(
                f"Invalid metric: {metric_name}"
            )

    if len(
        str(report.get("episodes_sha256", ""))
    ) != 64:
        raise ValueError("Invalid episodes_sha256")

    return report
