from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "memorix"
    / "diagnostics"
    / "memorix_capacity_status.py"
)


class CapacityCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--simulate-active-items", result.stdout)
        self.assertIn("--capacity", result.stdout)

    def test_empty_runtime_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            result = self.run_cli(
                "--runtime-root",
                str(root),
                "--capacity",
                "100",
                "--compact",
            )
            self.assertFalse(root.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["pressure_level"], "stable")
        self.assertEqual(payload["available_slots"], 100)
        self.assertFalse(payload["simulated"])

    def test_six_million_item_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            result = self.run_cli(
                "--runtime-root",
                str(root),
                "--capacity",
                "50000",
                "--simulate-active-items",
                "6000000",
                "--pretty",
            )
            self.assertFalse(root.exists())

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["active_memories"], 6_000_000)
        self.assertEqual(payload["pressure_level"], "critical")
        self.assertEqual(payload["available_slots"], 0)
        self.assertFalse(payload["admission_allowed"])
        self.assertTrue(payload["simulated"])
        self.assertTrue(payload["observation_only"])
        self.assertFalse(payload["applies_changes"])

    def test_repository_runtime_rejected(self) -> None:
        root = (
            Path(__file__).resolve().parents[2]
            / "memory"
            / "runtime"
        )
        result = self.run_cli(
            "--runtime-root",
            str(root),
        )
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["status"], "validation_failed")


if __name__ == "__main__":
    unittest.main()
