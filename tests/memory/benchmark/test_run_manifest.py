from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.global_contracts import BenchmarkMode, BenchmarkSize, BenchmarkSuite
from memory.benchmark.run_manifest import (
    EnvironmentSnapshot,
    RunRequest,
    build_manifest,
    load_manifest,
    write_manifest_atomic,
)


class RunManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.environment = EnvironmentSnapshot(
            captured_at_utc="2026-07-23T12:00:00Z",
            platform="Windows",
            platform_release="11",
            architecture="64bit",
            machine="benchmark-host",
            processor="test-cpu",
            python_version="3.10.0",
            python_executable="python",
            bun_version="1.3.14",
            git_commit="abcdef1234567890",
            git_dirty=False,
            repository_root=str(self.repository_root),
            hardware_id="a" * 64,
        )

    def request(self, mode: BenchmarkMode) -> RunRequest:
        return RunRequest(
            mode=mode,
            suite=BenchmarkSuite.AGENT,
            size=BenchmarkSize.TINY,
            seed=1001,
            task_id="task_001",
            dataset_id="dataset_v1",
            prompt_version="prompt_v1",
            model_id="model_v1",
            model_parameters={"temperature": 0},
            tool_budget=20,
            turn_budget=12,
            timeout_seconds=300,
            evaluator_version="deterministic_v1",
            paired_run_group_id="pair_001",
        )

    def test_no_memory_requires_no_runtime(self) -> None:
        manifest = build_manifest(
            self.request(BenchmarkMode.NO_MEMORY),
            self.environment,
            runtime_root=None,
            created_at_utc="2026-07-23T12:00:00Z",
        )
        self.assertIsNone(manifest.runtime_root)
        manifest.validate(repository_root=self.repository_root)

    def test_memory_mode_requires_external_runtime(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires an isolated runtime_root"):
            build_manifest(
                self.request(BenchmarkMode.MEMORIX_CORE),
                self.environment,
                runtime_root=None,
                created_at_utc="2026-07-23T12:00:00Z",
            )
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            build_manifest(
                self.request(BenchmarkMode.MEMORIX_CORE),
                self.environment,
                runtime_root=self.repository_root / "runtime",
                created_at_utc="2026-07-23T12:00:00Z",
            )

    def test_manifest_round_trip_and_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            manifest = build_manifest(
                self.request(BenchmarkMode.MEMORIX_FULL),
                self.environment,
                runtime_root=Path(temporary_directory) / "runtime",
                created_at_utc="2026-07-23T12:00:00Z",
            )
            write_manifest_atomic(output, manifest)
            loaded = load_manifest(output)
            self.assertEqual(loaded.to_dict(), manifest.to_dict())
            with self.assertRaises(FileExistsError):
                write_manifest_atomic(output, manifest)

    def test_tampered_fingerprint_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            manifest = build_manifest(
                self.request(BenchmarkMode.NO_MEMORY),
                self.environment,
                runtime_root=None,
                created_at_utc="2026-07-23T12:00:00Z",
            )
            payload = manifest.to_dict()
            payload["configuration_fingerprint"] = "0" * 64
            output.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                load_manifest(output)

    def test_run_id_is_deterministic_for_same_inputs(self) -> None:
        first = build_manifest(
            self.request(BenchmarkMode.NO_MEMORY),
            self.environment,
            runtime_root=None,
            created_at_utc="2026-07-23T12:00:00Z",
        )
        second = build_manifest(
            self.request(BenchmarkMode.NO_MEMORY),
            self.environment,
            runtime_root=None,
            created_at_utc="2026-07-23T12:00:00Z",
        )
        self.assertEqual(first.run_id, second.run_id)


if __name__ == "__main__":
    unittest.main()
