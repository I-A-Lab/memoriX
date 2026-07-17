from __future__ import annotations
import json
from pathlib import Path
import subprocess,sys,tempfile,unittest
SCRIPT=Path(__file__).resolve().parents[2]/"scripts"/"memorix_memory_pressure_benchmark.py"
class MemoryPressureBenchmarkCliTests(unittest.TestCase):
 def test_cli_report(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)/"runtime"; output=Path(directory)/"report.json"; result=subprocess.run([sys.executable,str(SCRIPT),"--runtime-root",str(root),"--repetitions","1","--output",str(output),"--pretty"],capture_output=True,text=True,check=False); self.assertFalse(root.exists()); payload=json.loads(output.read_text())
  self.assertEqual(result.returncode,0,result.stderr); self.assertEqual(len(payload["results"]),4)
if __name__=="__main__": unittest.main()
