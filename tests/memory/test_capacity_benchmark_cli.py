from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "tools" / "memorix" / "research" / "memorix_capacity_benchmark.py"


class CapacityBenchmarkCliTests(unittest.TestCase):
    def test_cli_emits_four_synthetic_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime_root = Path(temp) / "runtime"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--runtime-root",
                    str(runtime_root),
                    "--repetitions",
                    "1",
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(len(payload["results"]), 4)
            self.assertEqual(
                payload["results"][-1]["active_items"],
                6_000_000,
            )
            self.assertFalse(runtime_root.exists())

    def test_cli_can_write_an_explicit_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            output = temp_root / "reports" / "capacity.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--runtime-root",
                    str(temp_root / "runtime"),
                    "--repetitions",
                    "1",
                    "--scenarios",
                    "10000",
                    "6000000",
                    "--output",
                    str(output),
                ],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))[
                    "results"
                ][1]["pressure_level"],
                "critical",
            )


if __name__ == "__main__":
    unittest.main()
