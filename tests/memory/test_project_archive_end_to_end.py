from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import torch

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.server import MemoriXMcpServer


class ProjectArchiveEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.paths = MemoryStoragePaths.from_runtime_root(
            self.temporary_directory.name
        )
        torch.manual_seed(42)
        self.gateway = self.make_gateway()

    def make_gateway(self) -> MemoriXGateway:
        return MemoriXGateway(
            storage_paths=self.paths,
            titan_d_model=16,
            titan_hidden_dim=16,
            titan_max_items=50,
            titan_device="cpu",
            titan_top_k=3,
            titan_min_score=0.0,
        )

    def record_source_event(
        self,
        *,
        event_id: str,
        content: str,
    ) -> None:
        self.gateway.record_memory_event(
            event_id=event_id,
            content=content,
            event_type="architecture_rule",
            source="project_archive_end_to_end",
            project_id="memorix",
            session_id="project_archive_e2e",
            importance=0.9,
            confidence=1.0,
            surprise=0.4,
            created_at="2026-07-16T16:00:00+00:00",
            archived_at="2026-07-16T16:01:00+00:00",
        )

    def test_gateway_flow_survives_restart_and_versions_snapshots(
        self,
    ) -> None:
        self.record_source_event(
            event_id="event_project_identity",
            content="memoriX is a long-term memory system.",
        )
        self.record_source_event(
            event_id="event_project_objective",
            content="Project history must remain durable.",
        )

        identity = self.gateway.record_project_archive_entry(
            entry_id="project_entry_identity",
            project_id="memorix",
            entry_type="identity",
            title="memoriX",
            content="Long-term memory for AI agents.",
            source_event_ids=("event_project_identity",),
            author="Elwen",
            created_at="2026-07-16T16:02:00+00:00",
            recorded_at="2026-07-16T16:03:00+00:00",
        )
        objective = self.gateway.record_project_archive_entry(
            entry_id="project_entry_objective",
            project_id="memorix",
            entry_type="objective",
            title="Durable project memory",
            content="Provide durable project memory.",
            source_event_ids=("event_project_objective",),
            author="Elwen",
            created_at="2026-07-16T16:04:00+00:00",
            recorded_at="2026-07-16T16:05:00+00:00",
        )

        first = self.gateway.rebuild_project_snapshot(
            "memorix",
            updated_at="2026-07-16T16:06:00+00:00",
        )

        restarted = self.make_gateway()
        entries = restarted.list_project_archive_entries(
            project_id="memorix"
        )
        latest = restarted.get_project_snapshot("memorix")
        second = restarted.rebuild_project_snapshot(
            "memorix",
            updated_at="2026-07-16T16:07:00+00:00",
        )

        self.assertEqual(entries, (identity, objective))
        self.assertEqual(first.version, 1)
        self.assertEqual(latest, first)
        self.assertEqual(second.version, 2)
        self.assertEqual(
            second.source_entry_ids,
            (identity.entry_id, objective.entry_id),
        )
        self.assertEqual(
            second.objectives,
            ("Provide durable project memory.",),
        )

        status = restarted.memory_status()
        self.assertEqual(status["project_archive_entries"], 2)
        self.assertEqual(status["project_archive_snapshots"], 2)
        self.assertEqual(status["hot_memories_total"], 0)
        self.assertFalse(self.paths.titan_neural_state.exists())
        self.assertFalse(self.paths.titan_metadata.exists())

    def test_mcp_protocol_round_trip(self) -> None:
        server = MemoriXMcpServer(self.gateway)

        def call(request_id: int, name: str, arguments: dict):
            response = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": arguments,
                    },
                }
            )
            self.assertNotIn("error", response)
            result = response["result"]
            self.assertFalse(result["isError"])
            return result["structuredContent"]

        identity = call(
            1,
            "memorix_project_entry_record",
            {
                "project_id": "memorix",
                "entry_type": "identity",
                "title": "memoriX",
                "content": "Long-term memory for AI agents.",
                "source_event_ids": ["event_mcp_identity"],
                "author": "Elwen",
            },
        )
        entries_payload = call(
            2,
            "memorix_project_entries_list",
            {"project_id": "memorix"},
        )
        snapshot = call(
            3,
            "memorix_project_snapshot_rebuild",
            {"project_id": "memorix"},
        )
        latest = call(
            4,
            "memorix_project_snapshot_get",
            {"project_id": "memorix"},
        )

        entries = entries_payload.get("items", entries_payload)
        self.assertEqual(identity["project_id"], "memorix")
        self.assertEqual(len(entries), 1)
        self.assertEqual(snapshot["version"], 1)
        self.assertEqual(latest, snapshot)
        self.assertFalse(self.paths.titan_neural_state.exists())
        self.assertFalse(self.paths.titan_metadata.exists())

    def test_runtime_paths_remain_outside_repository(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]

        for path in (
            self.paths.project_archive_entries,
            self.paths.project_archive_snapshots,
        ):
            self.assertFalse(path.is_relative_to(repository_root))


if __name__ == "__main__":
    unittest.main()
