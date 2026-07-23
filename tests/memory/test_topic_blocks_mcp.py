
from __future__ import annotations
import tempfile, unittest
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools
class TopicBlocksMcpTests(unittest.TestCase):
    def test_create_and_inspect(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway=MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(directory),titan_d_model=16,titan_hidden_dim=16,titan_max_items=20,titan_device="cpu")
            tools=MemoriXMcpTools(gateway)
            created=tools.call("memorix_topic_blocks",{"action":"create","topic":"coding","actor":"test"})
            self.assertTrue(created["ok"])
            inspected=tools.call("memorix_topic_blocks",{"action":"inspect"})
            self.assertEqual(len(inspected["blocks"]),1)
if __name__=="__main__": unittest.main()
