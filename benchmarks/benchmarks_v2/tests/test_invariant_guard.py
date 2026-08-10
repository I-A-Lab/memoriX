from __future__ import annotations

import pytest

from benchmarks.orchestrator.invariant_guard import InvariantGuard, InvariantViolation


class TestNoMemoryMcpServerDetected:
    def test_no_memory_mcp_server_detected(self, monkeypatch):
        """Guard aborts when MCP server is loaded in no_memory mode."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_mcp_server_loaded",
            lambda: True,
        )
        violations = guard.check()
        assert any("mcp_server" in v.violation_type for v in violations)


class TestNoMemoryToolCallDetected:
    def test_no_memory_tool_call_detected(self, monkeypatch):
        """Guard aborts when memory_retrieve is called in no_memory mode."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_memory_tool_called",
            lambda tool_name: tool_name == "memory_retrieve",
        )
        violations = guard.check()
        assert any("tool_call" in v.violation_type for v in violations)


class TestNoMemoryMemoryStoreDetected:
    def test_no_memory_memory_store_detected(self, monkeypatch):
        """Guard aborts when memory_store is called in no_memory mode."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_memory_tool_called",
            lambda tool_name: tool_name == "memory_store",
        )
        violations = guard.check()
        assert any("memory_store" in v.violation_type for v in violations)


class TestNoMemoryRuntimeDirDetected:
    def test_no_memory_runtime_dir_detected(self, monkeypatch):
        """Guard aborts when runtime dir is created in no_memory mode."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_runtime_dir_created",
            lambda: True,
        )
        violations = guard.check()
        assert any("runtime_dir" in v.violation_type for v in violations)


class TestNoMemoryPluginDetected:
    def test_no_memory_plugin_detected(self, monkeypatch):
        """Guard aborts when plugin is loaded in no_memory mode."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_plugin_loaded",
            lambda: True,
        )
        violations = guard.check()
        assert any("plugin" in v.violation_type for v in violations)


class TestMemorixCoreAllowsMemoryTools:
    def test_memorix_core_allows_memory_tools(self, monkeypatch):
        """Guard does NOT abort for memorix_core mode."""
        guard = InvariantGuard(mode="memorix_core")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_mcp_server_loaded",
            lambda: True,
        )
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_memory_tool_called",
            lambda tool_name: True,
        )
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_plugin_loaded",
            lambda: True,
        )
        violations = guard.check()
        assert len(violations) == 0


class TestNoViolationsNoFalsePositive:
    def test_no_violations_no_false_positive(self, monkeypatch):
        """Guard with no violations returns empty list."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_mcp_server_loaded",
            lambda: False,
        )
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_memory_tool_called",
            lambda tool_name: False,
        )
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_runtime_dir_created",
            lambda: False,
        )
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_plugin_loaded",
            lambda: False,
        )
        violations = guard.check()
        assert violations == []


class TestViolationLogging:
    def test_violation_logging(self, monkeypatch, caplog):
        """Violation details are correctly logged."""
        guard = InvariantGuard(mode="no_memory")
        monkeypatch.setattr(
            "benchmarks.orchestrator.invariant_guard._is_mcp_server_loaded",
            lambda: True,
        )
        with caplog.at_level("WARNING"):
            guard.check()
        assert any(
            "INVARIANT VIOLATION" in record.message
            or "violation" in record.message.lower()
            for record in caplog.records
        )


class TestInvariantViolationMessage:
    def test_invariant_violation_message(self):
        """Exception message contains violation details."""
        violation = InvariantViolation(
            violation_type="test_violation",
            details="Test detail message",
            mode="no_memory",
        )
        msg = str(violation)
        assert "test_violation" in msg
        assert "Test detail message" in msg
        assert "no_memory" in msg
