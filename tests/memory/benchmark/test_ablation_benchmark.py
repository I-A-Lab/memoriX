from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.ablation_benchmark import (
    run_ablation_benchmark,
    validate_ablation_report,
)


class AblationBenchmarkTests(unittest.TestCase):
    def test_full_run_contains_all_configurations(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_ablation_benchmark(
                output_root=Path(tmp) / "out"
            )

            self.assertEqual(
                report["configuration_count"],
                7,
            )

    def test_persistent_memory_effect_is_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_ablation_benchmark(
                output_root=Path(tmp) / "out"
            )

            self.assertGreater(
                report["effects"][
                    "persistent_memory_effect"
                ],
                0,
            )

    def test_multi_agent_effect_is_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_ablation_benchmark(
                output_root=Path(tmp) / "out"
            )

            self.assertGreater(
                report["effects"][
                    "multi_agent_effect"
                ],
                0,
            )

    def test_invalid_configuration_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_ablation_benchmark(
                    output_root=Path(tmp) / "out",
                    configurations=["invalid"],
                )

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "existing.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                run_ablation_benchmark(
                    output_root=output
                )

    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_ablation_benchmark(
                output_root=output
            )

            report = validate_ablation_report(
                output / "ablation_report.json"
            )

            self.assertEqual(
                report["benchmark_version"],
                "37.1",
            )

    def test_tampered_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_ablation_benchmark(
                output_root=output
            )

            report_path = output / "ablation_report.json"
            data = json.loads(
                report_path.read_text(
                    encoding="utf-8"
                )
            )
            data["reference_quality_score"] = 2

            report_path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                validate_ablation_report(
                    report_path
                )


if __name__ == "__main__":
    unittest.main()
