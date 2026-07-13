"""Minimal JSON-RPC 2.0 MCP server over line-delimited stdio."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Mapping, TextIO

from memory.data import MemoryStoragePaths
from memory.gateway import MemoriXGateway
from memory.integrations.mcp.tools import (
    McpInvalidArgumentsError,
    McpToolError,
    MemoriXMcpTools,
    tool_result_payload,
)


JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "memorix-python"
SERVER_VERSION = "0.1.0"


class McpProtocolError(RuntimeError):
    """JSON-RPC/MCP protocol error."""

    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def build_gateway_from_environment() -> MemoriXGateway:
    """Build the MCP gateway from environment variables."""

    runtime_root = os.environ.get(
        "MEMORIX_RUNTIME_ROOT"
    )

    paths = (
        MemoryStoragePaths.from_runtime_root(
            runtime_root
        )
        if runtime_root
        else None
    )

    kwargs: dict[str, Any] = {
        "titan_d_model": int(
            os.environ.get(
                "MEMORIX_TITAN_D_MODEL",
                "256",
            )
        ),
        "titan_hidden_dim": int(
            os.environ.get(
                "MEMORIX_TITAN_HIDDEN_DIM",
                "256",
            )
        ),
        "titan_max_items": int(
            os.environ.get(
                "MEMORIX_TITAN_MAX_ITEMS",
                "50000",
            )
        ),
        "titan_device": os.environ.get(
            "MEMORIX_TITAN_DEVICE",
            "cpu",
        ),
        "titan_top_k": int(
            os.environ.get(
                "MEMORIX_TITAN_TOP_K",
                "5",
            )
        ),
        "titan_min_score": float(
            os.environ.get(
                "MEMORIX_TITAN_MIN_SCORE",
                "0.12",
            )
        ),
    }

    if paths is not None:
        kwargs["storage_paths"] = paths

    return MemoriXGateway(**kwargs)


class MemoriXMcpServer:
    """Handle line-delimited JSON-RPC MCP requests."""

    def __init__(
        self,
        gateway: MemoriXGateway,
    ) -> None:
        self._tools = MemoriXMcpTools(gateway)

    def handle_request(
        self,
        request: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """Handle one JSON-RPC request or notification."""

        if not isinstance(request, Mapping):
            raise McpProtocolError(
                -32600,
                "Invalid Request",
            )

        if request.get("jsonrpc") != JSONRPC_VERSION:
            raise McpProtocolError(
                -32600,
                "jsonrpc must be '2.0'.",
            )

        request_id = request.get("id")
        method = request.get("method")

        if not isinstance(method, str):
            raise McpProtocolError(
                -32600,
                "method must be a string.",
            )

        params = request.get("params", {})

        if not isinstance(params, Mapping):
            raise McpProtocolError(
                -32602,
                "params must be an object.",
            )

        if method.startswith("notifications/"):
            return None

        if request_id is None:
            return None

        result = self._dispatch(
            method,
            dict(params),
        )

        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    def _dispatch(
        self,
        method: str,
        params: dict[str, Any],
    ) -> Any:
        """Dispatch one MCP method."""

        if method == "initialize":
            return {
                "protocolVersion": (
                    MCP_PROTOCOL_VERSION
                ),
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    }
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
            }

        if method == "ping":
            return {}

        if method == "tools/list":
            return {
                "tools": self._tools.list_tools()
            }

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get(
                "arguments",
                {},
            )

            if not isinstance(name, str):
                raise McpProtocolError(
                    -32602,
                    "tools/call requires a string name.",
                )

            try:
                value = self._tools.call(
                    name,
                    arguments,
                )
            except McpInvalidArgumentsError as error:
                raise McpProtocolError(
                    -32602,
                    str(error),
                ) from error
            except McpToolError as error:
                raise McpProtocolError(
                    -32001,
                    str(error),
                ) from error
            except (
                ValueError,
                TypeError,
                LookupError,
                RuntimeError,
            ) as error:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": str(error),
                        }
                    ],
                    "isError": True,
                }

            return tool_result_payload(value)

        raise McpProtocolError(
            -32601,
            f"Method not found: {method}",
        )

    def error_response(
        self,
        request_id: Any,
        error: McpProtocolError,
    ) -> dict[str, Any]:
        """Build one JSON-RPC error response."""

        payload: dict[str, Any] = {
            "code": error.code,
            "message": error.message,
        }

        if error.data is not None:
            payload["data"] = error.data

        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": payload,
        }

    def serve(
        self,
        input_stream: TextIO = sys.stdin,
        output_stream: TextIO = sys.stdout,
        error_stream: TextIO = sys.stderr,
    ) -> int:
        """Run the line-delimited stdio server."""

        for raw_line in input_stream:
            line = raw_line.strip()

            if not line:
                continue

            request_id: Any = None

            try:
                decoded = json.loads(line)

                if isinstance(decoded, Mapping):
                    request_id = decoded.get("id")

                response = self.handle_request(
                    decoded
                )

                if response is None:
                    continue

            except json.JSONDecodeError as error:
                response = self.error_response(
                    None,
                    McpProtocolError(
                        -32700,
                        "Parse error",
                        {
                            "line": error.lineno,
                            "column": error.colno,
                        },
                    ),
                )

            except McpProtocolError as error:
                response = self.error_response(
                    request_id,
                    error,
                )

            except Exception as error:
                print(
                    (
                        "Unexpected MCP server error: "
                        f"{error}"
                    ),
                    file=error_stream,
                    flush=True,
                )

                response = self.error_response(
                    request_id,
                    McpProtocolError(
                        -32603,
                        "Internal error",
                    ),
                )

            output_stream.write(
                json.dumps(
                    response,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            output_stream.write("\n")
            output_stream.flush()

        return 0


def main() -> int:
    """Launch the default memoriX MCP server.

    Any diagnostic output produced while Titan is initialized is redirected
    to stderr so stdout remains reserved for JSON-RPC responses.
    """

    from contextlib import redirect_stdout

    with redirect_stdout(sys.stderr):
        gateway = build_gateway_from_environment()

    server = MemoriXMcpServer(gateway)
    return server.serve()


if __name__ == "__main__":
    raise SystemExit(main())
