from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PolicySearchCliTests(unittest.TestCase):
    def test_cli_runs_from_repository_root(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        script = project_root / "scripts" / "memorix_policy_search.py"
        with tempfile.TemporaryDirectory() as parent:
            runtime = Path(parent) / "missing-runtime"
            completed = subprocess.run(
                [sys.executable, str(script), "--runtime-root", str(runtime), "--max-trials", "3", "--simulate-memory-count", "100000", "--assessment-limit", "2"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["search_result"]["trial_count"], 3)
            self.assertEqual(payload["runtime_case_count"], 2)
            self.assertFalse(runtime.exists())
