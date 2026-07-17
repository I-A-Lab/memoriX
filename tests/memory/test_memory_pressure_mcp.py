from __future__ import annotations
import json
import tempfile
import unittest
from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import McpInvalidArgumentsError, MemoriXMcpTools

class MemoryPressureMcpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.paths=MemoryStoragePaths.from_runtime_root(self.temp.name)
        self.gateway=object.__new__(MemoriXGateway)
        self.gateway._paths=self.paths
        self.tools=MemoriXMcpTools(self.gateway)

    def test_status_simulation_is_read_only(self):
        result=self.tools.call("memorix_memory_pressure_status",{"simulate_count":6000000,"assessment_limit":1})
        self.assertEqual(result["snapshot"]["memory_count"],6000000)
        self.assertFalse(result["cold_site_accessed"])
        self.assertFalse(self.paths.titan_metadata.exists())
        self.assertFalse(self.paths.cold_archive_events.exists())

    def test_inspect_reads_one_metadata_item(self):
        self.paths.titan_metadata.parent.mkdir(parents=True,exist_ok=True)
        self.paths.titan_metadata.write_text(json.dumps({"memory_id":"m1","stored_at":"2020-01-01T00:00:00+00:00","active":False,"metadata":{"importance":0}})+"\n",encoding="utf-8")
        result=self.tools.call("memorix_memory_pressure_inspect",{"memory_id":"m1"})
        self.assertEqual(result["memory_id"],"m1")
        self.assertFalse(self.paths.cold_archive_events.exists())

    def test_invalid_status_arguments_are_rejected(self):
        with self.assertRaises(McpInvalidArgumentsError): self.tools.call("memorix_memory_pressure_status",{"assessment_limit":-1})

if __name__ == "__main__": unittest.main()
