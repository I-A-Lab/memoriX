from __future__ import annotations

import tempfile
import unittest

import torch

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import (
    McpInvalidArgumentsError,
    McpUnknownToolError,
    MemoriXMcpTools,
    tool_result_payload,
)


class McpToolsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.paths = (
            MemoryStoragePaths.from_runtime_root(
                self.temporary_directory.name
            )
        )

        torch.manual_seed(42)

        self.gateway = MemoriXGateway(
            storage_paths=self.paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

        self.tools = MemoriXMcpTools(
            self.gateway
        )


class McpToolDeclarationTests(McpToolsTestCase):
    def test_all_expected_tools_are_declared(self) -> None:
        names = {
            tool["name"]
            for tool in self.tools.list_tools()
        }

        self.assertEqual(
            names,
            {
                "memorix_record_event",
                "memorix_context",
                "memorix_search_cold_history",
                "memorix_propose_candidate",
                "memorix_list_candidates",
                "memorix_validate_candidate",
                "memorix_reject_candidate",
                "memorix_forget_memory",
                "memorix_run_consolidation",
                "memorix_run_nightly",
                "memorix_capacity_status",
                "memorix_capacity_plan",
                "memorix_capacity_prune",
                "memorix_memory_pressure_status",
                "memorix_memory_pressure_inspect",
                "memorix_retention_ranking_status",
                "memorix_retention_ranking_inspect",
                "memorix_adaptive_routing_plan",
                "memorix_policy_search",
                "memorix_policy_lifecycle",
                "memorix_topic_blocks",
                "memorix_consolidation",
            "memorix_observability",
                "memorix_project_entry_record",
                "memorix_project_entries_list",
                "memorix_project_snapshot_rebuild",
                "memorix_project_snapshot_get",
                "memorix_status",
            },
        )


class McpHierarchicalRetrievalContractTests(McpToolsTestCase):
    def test_record_and_context_falls_back_to_short_term(
        self,
    ) -> None:
        self.tools.call(
            "memorix_record_event",
            {
                "content": (
                    "Cold-only MCP token "
                    "MCP-COLD-8821."
                ),
                "event_type": "architecture_rule",
                "source": "unit_test",
                "importance": 0.9,
            },
        )

        hot = self.tools.call(
            "memorix_context",
            {
                "query": "MCP-COLD-8821",
            },
        )

        cold = self.tools.call(
            "memorix_search_cold_history",
            {
                "query": "MCP-COLD-8821",
            },
        )

        self.assertEqual(
            hot.source.value,
            "short_term",
        )
        self.assertEqual(len(hot.matches), 1)
        self.assertEqual(
            cold.source.value,
            "cold_audit",
        )
        self.assertEqual(len(cold.matches), 1)

    def test_candidate_validation_enters_hot_only(
        self,
    ) -> None:
        candidate = self.tools.call(
            "memorix_propose_candidate",
            {
                "content": (
                    "MCP validated memory belongs "
                    "to Titan."
                ),
                "reason": "MCP lifecycle test.",
                "source_event_ids": [
                    "event_mcp_candidate_001"
                ],
            },
        )

        memory = self.tools.call(
            "memorix_validate_candidate",
            {
                "candidate_id": (
                    candidate.candidate_id
                ),
                "validated_by": "human_reviewer",
                "validation_reason": "Approved.",
            },
        )

        hot = self.tools.call(
            "memorix_context",
            {
                "query": "MCP validated memory Titan",
            },
        )

        self.assertEqual(
            hot.matches[0].memory_id,
            memory.memory_id,
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )


class McpToolValidationTests(McpToolsTestCase):
    def test_unknown_tool_is_rejected(self) -> None:
        with self.assertRaises(
            McpUnknownToolError
        ):
            self.tools.call(
                "memorix_unknown",
                {},
            )

    def test_missing_required_text_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            McpInvalidArgumentsError
        ):
            self.tools.call(
                "memorix_context",
                {},
            )


class McpProjectArchiveTests(McpToolsTestCase):
    def test_project_archive_lifecycle_stays_out_of_titan(self) -> None:
        self.tools.call(
            "memorix_project_entry_record",
            {
                "project_id": "memorix",
                "entry_type": "identity",
                "title": "memoriX",
                "content": "Long-term memory for AI agents.",
                "source_event_ids": ["event_identity"],
                "author": "Elwen",
            },
        )
        self.tools.call(
            "memorix_project_entry_record",
            {
                "project_id": "memorix",
                "entry_type": "objective",
                "title": "Objective",
                "content": "Provide durable project memory.",
                "source_event_ids": ["event_objective"],
                "author": "Elwen",
            },
        )

        entries = self.tools.call(
            "memorix_project_entries_list",
            {"project_id": "memorix"},
        )
        snapshot = self.tools.call(
            "memorix_project_snapshot_rebuild",
            {"project_id": "memorix"},
        )
        latest = self.tools.call(
            "memorix_project_snapshot_get",
            {"project_id": "memorix"},
        )

        self.assertEqual(len(entries), 2)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(latest, snapshot)
        self.assertFalse(self.paths.titan_neural_state.exists())
        self.assertFalse(self.paths.titan_metadata.exists())

    def test_missing_project_snapshot_is_null(self) -> None:
        self.assertIsNone(
            self.tools.call(
                "memorix_project_snapshot_get",
                {"project_id": "missing"},
            )
        )

    def test_invalid_project_entry_type_is_rejected(self) -> None:
        with self.assertRaises(McpInvalidArgumentsError):
            self.tools.call(
                "memorix_project_entry_record",
                {
                    "project_id": "memorix",
                    "entry_type": "invalid",
                    "title": "Invalid",
                    "content": "Invalid",
                    "source_event_ids": ["event_invalid"],
                    "author": "Elwen",
                },
            )


class McpStructuredContentTests(unittest.TestCase):
    def test_array_result_is_wrapped_in_object(self) -> None:
        payload = tool_result_payload(
            [{"candidate_id": "candidate_test"}]
        )

        self.assertEqual(
            payload["structuredContent"],
            {
                "value": [
                    {
                        "candidate_id": "candidate_test"
                    }
                ]
            },
        )

    def test_object_result_remains_direct(self) -> None:
        payload = tool_result_payload(
            {
                "retrieval_contract": (
                    "short_term_then_hot_then_cold_fallback"
                )
            }
        )

        self.assertEqual(
            payload["structuredContent"],
            {
                "retrieval_contract": (
                    "short_term_then_hot_then_cold_fallback"
                )
            },
        )


class McpTargetedSupersessionTests(McpToolsTestCase):
    def test_validate_candidate_schema_declares_supersedes_id(
        self,
    ) -> None:
        definition = next(
            tool
            for tool in self.tools.list_tools()
            if tool["name"]
            == "memorix_validate_candidate"
        )

        properties = definition["inputSchema"][
            "properties"
        ]

        self.assertEqual(
            properties["supersedes_memory_id"],
            {"type": ["string", "null"]},
        )
        self.assertNotIn(
            "supersedes_memory_id",
            definition["inputSchema"]["required"],
        )

    def test_validate_candidate_supersedes_exact_memory_through_mcp(
        self,
    ) -> None:
        original = self.tools.call(
            "memorix_propose_candidate",
            {
                "content": (
                    "The MCP primary color is blue."
                ),
                "reason": "MCP supersession test.",
                "source_event_ids": [
                    "event_mcp_supersede_001"
                ],
            },
        )

        original_memory = self.tools.call(
            "memorix_validate_candidate",
            {
                "candidate_id": (
                    original.candidate_id
                ),
                "validated_by": "human_reviewer",
                "validation_reason": "Approved.",
            },
        )

        update = self.tools.call(
            "memorix_propose_candidate",
            {
                "content": (
                    "The MCP primary color is violet."
                ),
                "reason": "MCP supersession test.",
                "source_event_ids": [
                    "event_mcp_supersede_002"
                ],
            },
        )

        updated_memory = self.tools.call(
            "memorix_validate_candidate",
            {
                "candidate_id": update.candidate_id,
                "validated_by": "human_reviewer",
                "validation_reason": (
                    "Approved correction."
                ),
                "supersedes_memory_id": (
                    original_memory.memory_id
                ),
            },
        )

        self.assertEqual(
            updated_memory.supersedes_memory_id,
            original_memory.memory_id,
        )
        self.assertEqual(updated_memory.version, 2)

        all_memories = {
            memory.memory_id: memory
            for memory in self.gateway._hot_site.list_memories()
        }

        self.assertFalse(
            all_memories[original_memory.memory_id].active
        )
        self.assertTrue(
            all_memories[updated_memory.memory_id].active
        )

        hot = self.tools.call(
            "memorix_context",
            {"query": "MCP primary color"},
        )

        self.assertNotIn(
            original_memory.memory_id,
            [
                match.memory_id
                for match in hot.matches
            ],
        )
        self.assertFalse(
            self.paths.cold_archive_events.exists()
        )


if __name__ == "__main__":
    unittest.main()
