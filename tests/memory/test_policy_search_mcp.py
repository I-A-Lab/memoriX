from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools

class PolicySearchMcpTests(unittest.TestCase):
    def test_gateway_and_mcp_are_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            gateway = MemoriXGateway(storage_paths=MemoryStoragePaths.from_runtime_root(Path(directory)))
            result = gateway.policy_search(max_trials=3, simulate_memory_count=1000, assessment_limit=2)
            self.assertEqual(result["search_result"]["trial_count"], 3)
            self.assertFalse(result["policy_applied"])
            tools = MemoriXMcpTools(gateway)
            self.assertIn("memorix_policy_search", {item["name"] for item in tools.list_tools()})
            called = tools.call("memorix_policy_search", {"max_trials": 2, "simulate_memory_count": 10, "assessment_limit": 1})
            self.assertEqual(called["search_result"]["trial_count"], 2)

if __name__ == "__main__": unittest.main()
