from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import MemoriXMcpTools


class ScopedRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        torch.manual_seed(43)
        self.gateway = MemoriXGateway(
            storage_paths=MemoryStoragePaths.from_runtime_root(
                self.temporary.name
            ),
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=10,
            titan_min_score=0.0,
        )

    def validate(self, project_id: str, user_id: str, value: str):
        candidate = self.gateway.propose_memory_candidate(
            content=(
                f"Tenant {user_id} in project {project_id} uses "
                f"timezone token {value}."
            ),
            reason="Scoped retrieval test.",
            source_event_ids=(f"event-{project_id}-{user_id}-{value}",),
            importance=1.0,
            confidence=1.0,
            surprise=0.8,
            metadata={
                "project_id": project_id,
                "user_id": user_id,
                "decision_key": "timezone",
                "value": value,
            },
        )
        return self.gateway.validate_memory_candidate(
            candidate.candidate_id,
            validated_by="test_reviewer",
            validation_reason="Approved.",
        )

    def test_combined_scope_filters_before_ranking(self):
        expected = self.validate("PROJECT-A", "USER-A", "UTC-A")
        self.validate("PROJECT-A", "USER-B", "UTC-B")
        self.validate("PROJECT-B", "USER-A", "UTC-C")

        result = self.gateway.retrieve_memory(
            "What is the timezone token?",
            top_k=10,
            project_id="PROJECT-A",
            user_id="USER-A",
        )

        self.assertEqual(
            [match.memory_id for match in result.matches],
            [expected.memory_id],
        )
        self.assertTrue(
            all(
                match.metadata.get("project_id") == "PROJECT-A"
                and match.metadata.get("user_id") == "USER-A"
                for match in result.matches
            )
        )

    def test_single_scope_filters_and_empty_intersection(self):
        project_a_user_a = self.validate(
            "PROJECT-A", "USER-A", "UTC-A"
        )
        project_a_user_b = self.validate(
            "PROJECT-A", "USER-B", "UTC-B"
        )
        project_b_user_a = self.validate(
            "PROJECT-B", "USER-A", "UTC-C"
        )

        by_project = self.gateway.retrieve_memory(
            "timezone token",
            top_k=10,
            project_id="PROJECT-A",
        )
        self.assertEqual(
            {match.memory_id for match in by_project.matches},
            {project_a_user_a.memory_id, project_a_user_b.memory_id},
        )

        by_user = self.gateway.retrieve_memory(
            "timezone token",
            top_k=10,
            user_id="USER-A",
        )
        self.assertEqual(
            {match.memory_id for match in by_user.matches},
            {project_a_user_a.memory_id, project_b_user_a.memory_id},
        )

        empty = self.gateway.retrieve_memory(
            "timezone token",
            project_id="PROJECT-B",
            user_id="USER-B",
        )
        self.assertEqual(empty.matches, ())

    def test_mcp_context_propagates_scope(self):
        expected = self.validate("PROJECT-A", "USER-A", "UTC-A")
        self.validate("PROJECT-A", "USER-B", "UTC-B")
        tools = MemoriXMcpTools(self.gateway)

        definitions = {
            item["name"]: item
            for item in tools.list_tools()
        }
        properties = definitions["memorix_context"]["inputSchema"][
            "properties"
        ]
        self.assertIn("project_id", properties)
        self.assertIn("user_id", properties)

        result = tools.call(
            "memorix_context",
            {
                "query": "timezone token",
                "project_id": "PROJECT-A",
                "user_id": "USER-A",
                "top_k": 10,
            },
        )
        self.assertEqual(
            [match.memory_id for match in result.matches],
            [expected.memory_id],
        )

    def test_blank_scope_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "project_id"):
            self.gateway.retrieve_memory(
                "timezone token",
                project_id="   ",
            )


if __name__ == "__main__":
    unittest.main()
