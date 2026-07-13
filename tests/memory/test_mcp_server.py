from __future__ import annotations

import io
import json
import tempfile
import unittest

import torch

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.server import (
    MCP_PROTOCOL_VERSION,
    MemoriXMcpServer,
)


class McpServerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        paths = MemoryStoragePaths.from_runtime_root(
            self.temporary_directory.name
        )

        torch.manual_seed(42)

        gateway = MemoriXGateway(
            storage_paths=paths,
            titan_d_model=32,
            titan_hidden_dim=32,
            titan_max_items=100,
            titan_device="cpu",
            titan_top_k=5,
            titan_min_score=0.0,
        )

        self.server = MemoriXMcpServer(
            gateway
        )

    def request(
        self,
        request_id: int,
        method: str,
        params: dict | None = None,
    ):
        return self.server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )


class McpInitializationTests(McpServerTestCase):
    def test_initialize_returns_server_info(self) -> None:
        response = self.request(
            1,
            "initialize",
            {
                "protocolVersion": (
                    MCP_PROTOCOL_VERSION
                ),
                "capabilities": {},
                "clientInfo": {
                    "name": "unit-test",
                    "version": "1.0",
                },
            },
        )

        self.assertEqual(
            response["result"]["protocolVersion"],
            MCP_PROTOCOL_VERSION,
        )
        self.assertEqual(
            response["result"]["serverInfo"]["name"],
            "memorix-python",
        )


class McpToolProtocolTests(McpServerTestCase):
    def test_tools_list_returns_definitions(self) -> None:
        response = self.request(
            2,
            "tools/list",
        )

        tools = response["result"]["tools"]

        self.assertEqual(len(tools), 11)
        self.assertIn(
            "memorix_context",
            {
                tool["name"]
                for tool in tools
            },
        )

    def test_tools_call_returns_structured_content(
        self,
    ) -> None:
        response = self.request(
            3,
            "tools/call",
            {
                "name": "memorix_status",
                "arguments": {},
            },
        )

        result = response["result"]

        self.assertFalse(result["isError"])
        self.assertEqual(
            result["structuredContent"][
                "retrieval_contract"
            ],
            "hot_site_only_no_cold_fallback",
        )

    def test_tool_domain_error_is_returned_as_mcp_error(
        self,
    ) -> None:
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "memorix_context",
                "arguments": {
                    "query": "",
                },
            },
        }

        input_stream = io.StringIO(
            json.dumps(request) + "\n"
        )
        output_stream = io.StringIO()
        error_stream = io.StringIO()

        exit_code = self.server.serve(
            input_stream=input_stream,
            output_stream=output_stream,
            error_stream=error_stream,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            error_stream.getvalue(),
            "",
        )

        response = json.loads(
            output_stream.getvalue()
        )

        self.assertIn("error", response)
        self.assertEqual(
            response["error"]["code"],
            -32602,
        )
        self.assertEqual(
            response["error"]["message"],
            "query must be a non-empty string.",
        )


class McpStdioTests(McpServerTestCase):
    def test_line_delimited_stdio_round_trip(self) -> None:
        request_lines = "\n".join(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {},
                    }
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": (
                            "notifications/initialized"
                        ),
                        "params": {},
                    }
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }
                ),
            ]
        ) + "\n"

        input_stream = io.StringIO(
            request_lines
        )
        output_stream = io.StringIO()
        error_stream = io.StringIO()

        exit_code = self.server.serve(
            input_stream=input_stream,
            output_stream=output_stream,
            error_stream=error_stream,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            error_stream.getvalue(),
            "",
        )

        responses = [
            json.loads(line)
            for line in output_stream.getvalue().splitlines()
        ]

        self.assertEqual(len(responses), 2)
        self.assertEqual(
            responses[0]["id"],
            1,
        )
        self.assertEqual(
            responses[1]["id"],
            2,
        )

    def test_invalid_json_returns_parse_error(self) -> None:
        input_stream = io.StringIO(
            "not-json\n"
        )
        output_stream = io.StringIO()

        self.server.serve(
            input_stream=input_stream,
            output_stream=output_stream,
            error_stream=io.StringIO(),
        )

        response = json.loads(
            output_stream.getvalue()
        )

        self.assertEqual(
            response["error"]["code"],
            -32700,
        )


if __name__ == "__main__":
    unittest.main()
