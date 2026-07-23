"""MCP server integration for the memoriX Python gateway."""

from memory.integrations.mcp.server import (
    MCP_PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    McpProtocolError,
    MemoriXMcpServer,
    build_gateway_from_environment,
)
from memory.integrations.mcp.tools import (
    TOOL_DEFINITIONS,
    McpInvalidArgumentsError,
    McpToolDefinition,
    McpToolError,
    McpUnknownToolError,
    MemoriXMcpTools,
)

__all__ = [
    "MCP_PROTOCOL_VERSION",
    "SERVER_NAME",
    "SERVER_VERSION",
    "TOOL_DEFINITIONS",
    "McpInvalidArgumentsError",
    "McpProtocolError",
    "McpToolDefinition",
    "McpToolError",
    "McpUnknownToolError",
    "MemoriXMcpServer",
    "MemoriXMcpTools",
    "build_gateway_from_environment",
]
