from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
SCRIPT=Path(__file__).resolve().parents[2]/"scripts"/"memorix_memory_pressure.py"
class MemoryPressureCliTests(unittest.TestCase):
    def run_cli(self,*args): return subprocess.run([sys.executable,str(SCRIPT),*args],capture_output=True,text=True,check=False)
    def test_help(self):
        result=self.run_cli("--help"); self.assertEqual(result.returncode,0); self.assertIn("--simulate-count",result.stdout)
    def test_empty_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"runtime"; result=self.run_cli("--runtime-root",str(root),"--compact"); self.assertFalse(root.exists())
        self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(json.loads(result.stdout)["snapshot"]["memory_count"],0)
    def test_simulation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/"runtime"; result=self.run_cli("--runtime-root",str(root),"--simulate-count","6000000","--assessment-limit","1","--pretty"); self.assertFalse(root.exists())
        payload=json.loads(result.stdout); self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(payload["snapshot"]["memory_count"],6000000); self.assertTrue(payload["simulated"])
    def test_invalid_limit(self):
        with tempfile.TemporaryDirectory() as directory: result=self.run_cli("--runtime-root",directory,"--assessment-limit","-1")
        self.assertEqual(result.returncode,2)
if __name__ == "__main__": unittest.main()
