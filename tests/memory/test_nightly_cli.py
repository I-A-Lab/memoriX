from __future__ import annotations
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'tools' / 'memorix' / 'operations' / 'memorix_nightly.py'

class NightlyCliTests(unittest.TestCase):
    def test_help(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--status-only', result.stdout)

    def test_status_only_without_state(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(SCRIPT), '--runtime-root', str(Path(directory)/'runtime'), '--status-only', '--compact'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('never_run', result.stdout)

    def test_repository_runtime_rejected(self):
        root = Path(__file__).resolve().parents[2] / 'memory' / 'runtime'
        result = subprocess.run([sys.executable, str(SCRIPT), '--runtime-root', str(root), '--status-only'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

if __name__ == '__main__':
    unittest.main()
