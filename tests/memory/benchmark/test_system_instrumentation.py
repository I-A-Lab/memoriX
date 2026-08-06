from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from memory.benchmark.system_instrumentation import (
    run_instrumented_command,
    validate_system_report,
)


class SystemInstrumentationTests(unittest.TestCase):
    def test_successful_command_produces_report_and_samples(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            report = run_instrumented_command(
                [sys.executable, "-c", "print('READY')"],
                working_directory=root,
                output_directory=output,
                timeout_seconds=5,
                sample_interval_seconds=0.02,
                ready_marker="READY",
            )
            self.assertEqual(report.exit_code, 0)
            self.assertFalse(report.timed_out)
            self.assertGreaterEqual(report.sample_count, 1)
            self.assertEqual(len(report.stdout_sha256), 64)
            self.assertTrue((output / "process_samples.jsonl").is_file())
            self.assertTrue((output / "system_report.json").is_file())
            validate_system_report(output / "system_report.json")

    def test_timeout_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = run_instrumented_command(
                [sys.executable, "-c", "import time; time.sleep(2)"],
                working_directory=root,
                output_directory=root / "output",
                timeout_seconds=0.2,
                sample_interval_seconds=0.02,
            )
            self.assertTrue(report.timed_out)
            self.assertLess(report.duration_ms, 3000)

    def test_directory_growth_is_measured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tracked = root / "tracked"
            command = [
                sys.executable,
                "-c",
                "from pathlib import Path; Path('tracked').mkdir(); Path('tracked/x.bin').write_bytes(b'x'*128)",
            ]
            report = run_instrumented_command(
                command,
                working_directory=root,
                output_directory=root / "output",
                timeout_seconds=5,
                tracked_directories={"runtime": tracked},
            )
            self.assertEqual(report.tracked_directories["runtime"]["growth_bytes"], 128)

    def test_non_empty_output_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            (output / "existing.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                run_instrumented_command(
                    [sys.executable, "-c", "print('x')"],
                    working_directory=root,
                    output_directory=output,
                    timeout_seconds=5,
                )

    def test_invalid_report_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_system_report(path)


if __name__ == "__main__":
    unittest.main()
