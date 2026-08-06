from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.load_robustness import run_load_robustness, validate_load_robustness_report


class LoadRobustnessTests(unittest.TestCase):
    def test_full_run_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_load_robustness(output_root=Path(tmp) / "out", record_count=100, corruption_lines=2, near_capacity_ratio=0.9, timeout_seconds=0.1)
            self.assertEqual(report["metrics"]["success_rate"], 1.0)

    def test_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_load_robustness(output_root=Path(tmp) / "out", record_count=50, corruption_lines=4, near_capacity_ratio=0.9, timeout_seconds=0.1)
            self.assertEqual(report["metrics"]["corruption_detection_rate"], 1.0)

    def test_timeout_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_load_robustness(output_root=Path(tmp) / "out", record_count=10, corruption_lines=1, near_capacity_ratio=0.9, timeout_seconds=0.1)
            self.assertEqual(report["metrics"]["timeout_enforcement_rate"], 1.0)

    def test_realistic_capacity_ratio_triggers_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_load_robustness(
                output_root=Path(tmp) / "out",
                record_count=5000,
                corruption_lines=3,
                near_capacity_ratio=0.95,
                timeout_seconds=0.1,
            )

            self.assertEqual(
                report["metrics"]["capacity_guard_rate"],
                1.0,
            )
            self.assertEqual(
                report["metrics"]["success_rate"],
                1.0,
            )

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "existing.txt").write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_load_robustness(output_root=output, record_count=10, corruption_lines=1, near_capacity_ratio=0.9, timeout_seconds=0.1)

    def test_invalid_capacity_ratio_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_load_robustness(output_root=Path(tmp) / "out", record_count=10, corruption_lines=1, near_capacity_ratio=1.5, timeout_seconds=0.1)

    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_load_robustness(output_root=output, record_count=10, corruption_lines=1, near_capacity_ratio=0.9, timeout_seconds=0.1)
            report = validate_load_robustness_report(output / "load_robustness_report.json")
            self.assertEqual(report["benchmark_version"], "38.1")

    def test_tampered_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_load_robustness(output_root=output, record_count=10, corruption_lines=1, near_capacity_ratio=0.9, timeout_seconds=0.1)
            report_path = output / "load_robustness_report.json"
            data = json.loads(report_path.read_text(encoding="utf-8"))
            data["metrics"]["success_rate"] = 2
            report_path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_load_robustness_report(report_path)


if __name__ == "__main__":
    unittest.main()
