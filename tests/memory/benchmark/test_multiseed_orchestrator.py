from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.multiseed_orchestrator import (
    run_multiseed_orchestrator,
    validate_multiseed_report,
)


class MultiSeedOrchestratorTests(unittest.TestCase):
    def test_full_run_aggregates_all_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_multiseed_orchestrator(
                output_root=Path(tmp) / "out",
                seeds=[11, 22, 33],
            )

            self.assertEqual(report["run_count"], 6)
            self.assertEqual(
                report["aggregates"]["no_memory"][
                    "task_completion_rate"
                ]["count"],
                3,
            )

    def test_memorix_outperforms_no_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_multiseed_orchestrator(
                output_root=Path(tmp) / "out",
                seeds=[1, 2],
            )

            delta = report["comparisons"][
                "memorix_core_minus_no_memory"
            ]["task_completion_rate"]

            self.assertGreater(delta, 0)

    def test_resume_skips_completed_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"

            run_multiseed_orchestrator(
                output_root=output,
                seeds=[7, 8],
            )

            report = run_multiseed_orchestrator(
                output_root=output,
                seeds=[7, 8],
                resume=True,
            )

            self.assertEqual(
                report["completed_run_count"],
                0,
            )
            self.assertEqual(
                report["resumed_run_count"],
                4,
            )

    def test_duplicate_seed_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_multiseed_orchestrator(
                    output_root=Path(tmp) / "out",
                    seeds=[1, 1],
                )

    def test_existing_output_requires_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            output.mkdir()
            (output / "existing.txt").write_text(
                "existing",
                encoding="utf-8",
            )

            with self.assertRaises(FileExistsError):
                run_multiseed_orchestrator(
                    output_root=output,
                    seeds=[1],
                )

    def test_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"

            run_multiseed_orchestrator(
                output_root=output,
                seeds=[3, 4],
            )

            report = validate_multiseed_report(
                output / "multiseed_report.json"
            )

            self.assertEqual(
                report["orchestrator_version"],
                "39.1",
            )

    def test_tampered_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"

            run_multiseed_orchestrator(
                output_root=output,
                seeds=[3, 4],
            )

            report_path = output / "multiseed_report.json"
            data = json.loads(
                report_path.read_text(encoding="utf-8")
            )
            data["run_count"] = 999
            report_path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                validate_multiseed_report(report_path)


if __name__ == "__main__":
    unittest.main()
