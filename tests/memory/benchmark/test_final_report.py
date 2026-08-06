from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.final_report import (
    generate_final_report,
    validate_final_report,
)


def _sample_multiseed_report() -> dict:
    summary = {
        "count": 3,
        "mean": 0.5,
        "median": 0.5,
        "stdev": 0.0,
        "min": 0.5,
        "max": 0.5,
        "ci95_low": 0.5,
        "ci95_high": 0.5,
    }

    memorix_summary = dict(summary)
    memorix_summary["mean"] = 1.0
    memorix_summary["median"] = 1.0
    memorix_summary["min"] = 1.0
    memorix_summary["max"] = 1.0
    memorix_summary["ci95_low"] = 1.0
    memorix_summary["ci95_high"] = 1.0

    return {
        "schema_version": 1,
        "orchestrator_version": "39.1",
        "suite": "sdlc",
        "seeds": [101, 202, 303],
        "modes": [
            "no_memory",
            "memorix_core",
        ],
        "run_count": 6,
        "aggregates": {
            "no_memory": {
                "task_completion_rate": summary,
            },
            "memorix_core": {
                "task_completion_rate": (
                    memorix_summary
                ),
            },
        },
        "comparisons": {
            "memorix_core_minus_no_memory": {
                "task_completion_rate": 0.5,
            }
        },
    }


class FinalReportTests(unittest.TestCase):
    def test_generation_creates_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )

            output = root / "report"

            report = generate_final_report(
                multiseed_report_path=source,
                output_root=output,
            )

            self.assertEqual(
                report["aggregate_row_count"],
                2,
            )
            self.assertTrue(
                (
                    output
                    / "aggregate_metrics.csv"
                ).is_file()
            )
            self.assertTrue(
                (
                    output
                    / "comparisons.csv"
                ).is_file()
            )
            self.assertTrue(
                (
                    output
                    / "chart_data.json"
                ).is_file()
            )
            self.assertTrue(
                (
                    output
                    / "benchmark_report.md"
                ).is_file()
            )

    def test_csv_contains_expected_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )
            output = root / "report"

            generate_final_report(
                multiseed_report_path=source,
                output_root=output,
            )

            with (
                output
                / "aggregate_metrics.csv"
            ).open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:
                rows = list(
                    csv.DictReader(handle)
                )

            self.assertEqual(len(rows), 2)

    def test_markdown_contains_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )
            output = root / "report"

            generate_final_report(
                multiseed_report_path=source,
                output_root=output,
            )

            markdown = (
                output
                / "benchmark_report.md"
            ).read_text(
                encoding="utf-8"
            )

            self.assertIn(
                "no_memory",
                markdown,
            )
            self.assertIn(
                "memorix_core",
                markdown,
            )

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )

            output = root / "report"
            output.mkdir()
            (
                output
                / "existing.txt"
            ).write_text(
                "existing",
                encoding="utf-8",
            )

            with self.assertRaises(
                FileExistsError
            ):
                generate_final_report(
                    multiseed_report_path=source,
                    output_root=output,
                )

    def test_unsupported_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"

            data = _sample_multiseed_report()
            data["orchestrator_version"] = "0"

            source.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                generate_final_report(
                    multiseed_report_path=source,
                    output_root=root / "report",
                )

    def test_final_report_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )
            output = root / "report"

            generate_final_report(
                multiseed_report_path=source,
                output_root=output,
            )

            report = validate_final_report(
                output / "final_report.json"
            )

            self.assertEqual(
                report["report_version"],
                "40.1",
            )

    def test_tampered_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "multiseed.json"
            source.write_text(
                json.dumps(
                    _sample_multiseed_report()
                ),
                encoding="utf-8",
            )
            output = root / "report"

            generate_final_report(
                multiseed_report_path=source,
                output_root=output,
            )

            report_path = (
                output
                / "final_report.json"
            )

            data = json.loads(
                report_path.read_text(
                    encoding="utf-8"
                )
            )
            data["run_count"] = 0
            report_path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                validate_final_report(
                    report_path
                )


if __name__ == "__main__":
    unittest.main()
