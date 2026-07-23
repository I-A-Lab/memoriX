from __future__ import annotations

import tempfile
import unittest

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools


class AdaptiveRoutingMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        paths = MemoryStoragePaths.from_runtime_root(self.temporary.name)
        gateway = object.__new__(MemoriXGateway)
        gateway._paths = paths
        self.paths = paths
        self.tools = MemoriXMcpTools(gateway)

    def test_plan_is_read_only(self) -> None:
        result = self.tools.call(
            "memorix_adaptive_routing_plan",
            {
                "target_id": "candidate-1",
                "retention_score": 0.9,
                "simulate_memory_count": 6_000_000,
                "assessment_limit": 1,
            },
        )
        self.assertEqual(result["target_id"], "candidate-1")
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["applied"])
        self.assertFalse(self.paths.titan_metadata.exists())

    def test_empty_target_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            self.tools.call("memorix_adaptive_routing_plan", {"target_id": " "})


if __name__ == "__main__":
    unittest.main()
