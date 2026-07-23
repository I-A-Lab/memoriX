from __future__ import annotations

import tempfile
import unittest

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import (
    McpInvalidArgumentsError,
    MemoriXMcpTools,
)


class RetentionRankingMcpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.paths = MemoryStoragePaths.from_runtime_root(
            self.temporary.name
        )
        self.gateway = object.__new__(MemoriXGateway)
        self.gateway._paths = self.paths
        self.tools = MemoriXMcpTools(self.gateway)

    def test_status_simulation_is_read_only(self) -> None:
        result = self.tools.call(
            "memorix_retention_ranking_status",
            {"simulate_count": 6_000_000, "assessment_limit": 1},
        )
        self.assertEqual(result["ranking"]["memory_count"], 6_000_000)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["applied"])
        self.assertFalse(self.paths.titan_metadata.exists())

    def test_inspect_unknown_memory_returns_none(self) -> None:
        result = self.tools.call(
            "memorix_retention_ranking_inspect",
            {"memory_id": "missing"},
        )
        self.assertIsNone(result)

    def test_invalid_limit_is_rejected(self) -> None:
        with self.assertRaises(McpInvalidArgumentsError):
            self.tools.call(
                "memorix_retention_ranking_status",
                {"assessment_limit": -1},
            )


if __name__ == "__main__":
    unittest.main()
