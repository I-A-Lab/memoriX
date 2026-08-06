from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.sdlc_benchmark import (
    run_sdlc_benchmark,
    validate_sdlc_report,
)


class SDLCBenchmarkTests(unittest.TestCase):
    def test_no_memory_exposes_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_sdlc_benchmark(
                output_root=Path(tmp) / "out",
                mode="no_memory",
            )

            self.assertLess(
                report["metrics"][
                    "task_completion_rate"
                ],
                1.0,
            )
            self.assertEqual(
                report["metrics"][
                    "regression_count"
                ],
                1,
            )

    def test_memorix_core_reuses_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_sdlc_benchmark(
                output_root=Path(tmp) / "out",
                mode="memorix_core",
            )

            self.assertEqual(
                report["metrics"][
                    "task_completion_rate"
                ],
                1.0,
            )
            self.assertEqual(
                report["metrics"][
                    "decision_reuse_accuracy"
                ],
                1.0,
            )

    def test_invalid_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_sdlc_benchmark(
                    output_root=Path(tmp) / "out",
                    mode="invalid",
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
                run_sdlc_benchmark(
                    output_root=output,
                    mode="no_memory",
                )

    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_sdlc_benchmark(
                output_root=output,
                mode="memorix_core",
            )

            report = validate_sdlc_report(
                output / "sdlc_report.json"
            )

            self.assertEqual(
                report["benchmark_version"],
                "36.1",
            )

    def test_tampered_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            run_sdlc_benchmark(
                output_root=output,
                mode="memorix_core",
            )

            report_path = output / "sdlc_report.json"
            data = json.loads(
                report_path.read_text(
                    encoding="utf-8"
                )
            )
            data["metrics"][
                "task_completion_rate"
            ] = 2

            report_path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                validate_sdlc_report(report_path)


if __name__ == "__main__":
    unittest.main()
