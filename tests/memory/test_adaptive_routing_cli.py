import json, subprocess, sys, tempfile, unittest
from pathlib import Path
class RoutingCliTests(unittest.TestCase):
    def test_cli_simulation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"runtime"
            proc=subprocess.run([sys.executable,"tools/memorix/diagnostics/memorix_adaptive_routing.py","--runtime-root",str(root),"--target-id","c1","--simulate-memory-count","6000000","--configured-capacity","50000"],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            data=json.loads(proc.stdout)
            self.assertTrue(data["dry_run"])
            self.assertFalse(data["runtime_modified"])
            self.assertFalse(root.exists())
if __name__=="__main__": unittest.main()
