import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RetentionRankingBenchmarkCliTests(unittest.TestCase):
    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            process = subprocess.run(
                [
                    sys.executable,
                    "scripts/memorix_retention_ranking_benchmark.py",
                    "--runtime-root",
                    str(Path(directory) / "runtime"),
                    "--repetitions",
                    "1",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["results"]), 4)


if __name__ == "__main__":
    unittest.main()
