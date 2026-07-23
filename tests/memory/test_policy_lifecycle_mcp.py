
from __future__ import annotations
import tempfile, unittest
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools
class PolicyLifecycleMcpTests(unittest.TestCase):
    def test_inspect_and_propose(self):
        with tempfile.TemporaryDirectory() as temporary:
            gateway=MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(temporary),titan_d_model=16,titan_hidden_dim=16,titan_max_items=20,titan_device="cpu")
            tools=MemoriXMcpTools(gateway)
            inspect=tools.call("memorix_policy_lifecycle",{"action":"inspect"})
            self.assertFalse(inspect["registry_exists"])
            proposed=tools.call("memorix_policy_lifecycle",{"action":"propose","version_id":"mcp-v1","actor":"tester"})
            self.assertTrue(proposed["policy_proposed"])
if __name__ == "__main__": unittest.main()
