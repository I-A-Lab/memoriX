from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools

class CapacityMcpTests(unittest.TestCase):
    def test_status_and_plan(self):
        with TemporaryDirectory() as tmp:
            gateway=MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(Path(tmp)), titan_d_model=8, titan_hidden_dim=8, titan_max_items=4)
            tools=MemoriXMcpTools(gateway)
            status=tools.call('memorix_capacity_status', {})
            self.assertEqual(status['configured_capacity'], 4)
            plan=tools.call('memorix_capacity_plan', {})
            self.assertTrue(plan['dry_run'])
if __name__ == '__main__': unittest.main()
