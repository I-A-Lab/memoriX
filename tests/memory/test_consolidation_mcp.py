import tempfile, unittest
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
class ConsolidationMcpTests(unittest.TestCase):
 def test_gateway_inspect(self):
  with tempfile.TemporaryDirectory() as root:
   gateway=MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(root),titan_d_model=16,titan_hidden_dim=16,titan_max_items=20,titan_device='cpu')
   self.assertFalse(gateway.consolidation_lifecycle(action='inspect')['registry_exists'])
if __name__=='__main__': unittest.main()
