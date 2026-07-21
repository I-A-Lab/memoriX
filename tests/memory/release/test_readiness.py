from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory.release import inspect_release_readiness


class ReleaseReadinessTests(unittest.TestCase):
    def test_repository_is_ready_with_external_runtime(self) -> None:
        project = Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as runtime:
            report = inspect_release_readiness(project, runtime)
        self.assertTrue(report.passed, report.to_dict())
        self.assertEqual(report.status, "ready")
        self.assertTrue(report.dry_run)
        self.assertFalse(report.runtime_modified)
        self.assertFalse(report.neural_model_loaded)

    def test_runtime_inside_repository_is_blocked(self) -> None:
        project = Path(__file__).resolve().parents[3]
        report = inspect_release_readiness(project, project / "runtime-probe")
        self.assertFalse(report.passed)
        failed = {check.name for check in report.checks if not check.passed}
        self.assertIn("runtime_outside_repository", failed)
