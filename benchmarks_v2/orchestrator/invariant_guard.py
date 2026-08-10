from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Module-level check functions (mockable for testing)
def _is_mcp_server_loaded() -> bool:
    """Check if an MCP server is loaded. Returns False by default."""
    return False


def _is_memory_tool_called(tool_name: str) -> bool:
    """Check if a memory tool was called. Returns False by default."""
    return False


def _is_runtime_dir_created() -> bool:
    """Check if a runtime directory was created. Returns False by default."""
    return False


def _is_plugin_loaded() -> bool:
    """Check if a plugin is loaded. Returns False by default."""
    return False


@dataclass(frozen=True, slots=True)
class InvariantViolation:
    """Represents an invariant violation."""
    violation_type: str
    details: str
    mode: str

    def __str__(self) -> str:
        return f"[{self.mode}] InvariantViolation({self.violation_type}): {self.details}"


class InvariantGuard:
    """Enforces no-memory invariants during benchmark execution."""

    def __init__(self, mode: str = "no_memory") -> None:
        self.mode = mode

    def check(self) -> List[InvariantViolation]:
        """Run all invariant checks and return any violations.

        In 'no_memory' mode, all checks are active.
        In 'memorix_core' mode, no checks are active (memory tools are allowed).
        """
        violations: List[InvariantViolation] = []

        if self.mode != "no_memory":
            return violations

        # Check MCP server
        if _is_mcp_server_loaded():
            violation = InvariantViolation(
                violation_type="mcp_server",
                details="MCP server is loaded in no_memory mode",
                mode=self.mode,
            )
            logger.warning("INVARIANT VIOLATION: %s", violation)
            violations.append(violation)

        # Check memory tool calls
        for tool_name in ["memory_retrieve", "memory_store"]:
            if _is_memory_tool_called(tool_name):
                violation = InvariantViolation(
                    violation_type="tool_call" if tool_name == "memory_retrieve" else "memory_store",
                    details=f"Memory tool '{tool_name}' called in no_memory mode",
                    mode=self.mode,
                )
                logger.warning("INVARIANT VIOLATION: %s", violation)
                violations.append(violation)

        # Check runtime dir
        if _is_runtime_dir_created():
            violation = InvariantViolation(
                violation_type="runtime_dir",
                details="Runtime directory created in no_memory mode",
                mode=self.mode,
            )
            logger.warning("INVARIANT VIOLATION: %s", violation)
            violations.append(violation)

        # Check plugin
        if _is_plugin_loaded():
            violation = InvariantViolation(
                violation_type="plugin",
                details="Plugin loaded in no_memory mode",
                mode=self.mode,
            )
            logger.warning("INVARIANT VIOLATION: %s", violation)
            violations.append(violation)

        return violations
