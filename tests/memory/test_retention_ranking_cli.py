import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RetentionRankingCliTests(unittest.TestCase):
    def test_cli_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.run(
                [
                    sys.executable,
                    "tools/memorix/diagnostics/memorix_retention_ranking.py",
                    "--runtime-root",
                    str(Path(directory) / "runtime"),
                    "--simulate-count",
                    "1000",
                    "--assessment-limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            payload = json.loads(process.stdout)
            self.assertEqual(payload["ranking"]["memory_count"], 1000)


if __name__ == "__main__":
    unittest.main()
