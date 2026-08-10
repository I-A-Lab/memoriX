from __future__ import annotations

import pytest

from benchmarks_v2.orchestrator.failure_classifier import (
    classify_failure,
    is_retryable,
    load_taxonomy,
)


class TestClassifyAPITimeout:
    def test_classify_api_timeout(self):
        """Returns TECH_API_TIMEOUT."""
        result = classify_failure("API request timed out after 30000ms connection timeout")
        assert result == "TECH_API_TIMEOUT"


class TestClassifyAPIAuth:
    def test_classify_api_auth(self):
        """Returns TECH_API_AUTH."""
        result = classify_failure("401 Unauthorized: Invalid API key provided")
        assert result == "TECH_API_AUTH"


class TestClassifyHostOOM:
    def test_classify_host_oom(self):
        """Returns TECH_HOST_OOM."""
        result = classify_failure("Out of memory: process killed by OS OOM killer")
        assert result == "TECH_HOST_OOM"


class TestClassifyMCPCrash:
    def test_classify_mcp_crash(self):
        """Returns TECH_MCP_CRASH."""
        result = classify_failure("MCP server process crashed unexpectedly with SIGSEGV")
        assert result == "TECH_MCP_CRASH"


class TestClassifyToolHallucination:
    def test_classify_tool_hallucination(self):
        """Returns AGENT_TOOL_HALLUCINATION."""
        result = classify_failure("Agent called non-existent tool nonexistent_tool_xyz")
        assert result == "AGENT_TOOL_HALLUCINATION"


class TestClassifyBashRecoveryFail:
    def test_classify_bash_recovery_fail(self):
        """Returns AGENT_BASH_RECOVERY_FAIL."""
        result = classify_failure("Agent failed to recover from bash command failure after retry")
        assert result == "AGENT_BASH_RECOVERY_FAIL"


class TestClassifyLogicLoop:
    def test_classify_logic_loop(self):
        """Returns AGENT_LOGIC_LOOP."""
        result = classify_failure("Agent entered infinite logic loop: repeated same action 50 times")
        assert result == "AGENT_LOGIC_LOOP"


class TestClassifyConstraintViolation:
    def test_classify_constraint_violation(self):
        """Returns AGENT_CONSTRAINT_VIOLATION."""
        result = classify_failure("Agent violated system constraint: file outside workspace boundary")
        assert result == "AGENT_CONSTRAINT_VIOLATION"


class TestClassifyFinalIncorrect:
    def test_classify_final_incorrect(self):
        """Returns AGENT_FINAL_INCORRECT."""
        result = classify_failure("Agent produced incorrect final output: expected 42 got 0")
        assert result == "AGENT_FINAL_INCORRECT"


class TestClassifyCurationLoss:
    def test_classify_curation_loss(self):
        """Returns MEM_CURATION_LOSS."""
        result = classify_failure("Memory curation loss: consolidated facts diverged from source")
        assert result == "MEM_CURATION_LOSS"


class TestClassifyRetrievalLoss:
    def test_classify_retrieval_loss(self):
        """Returns MEM_RETRIEVAL_LOSS."""
        result = classify_failure("Memory retrieval loss: memory_retrieve returned irrelevant results")
        assert result == "MEM_RETRIEVAL_LOSS"


class TestIsRetryableTechnical:
    def test_is_retryable_technical(self):
        """TECH_* returns True."""
        assert is_retryable("TECH_API_TIMEOUT") is True
        assert is_retryable("TECH_API_AUTH") is True
        assert is_retryable("TECH_HOST_OOM") is True
        assert is_retryable("TECH_MCP_CRASH") is True


class TestIsRetryableAgent:
    def test_is_retryable_agent(self):
        """AGENT_* returns False."""
        assert is_retryable("AGENT_TOOL_HALLUCINATION") is False
        assert is_retryable("AGENT_BASH_RECOVERY_FAIL") is False
        assert is_retryable("AGENT_LOGIC_LOOP") is False
        assert is_retryable("AGENT_CONSTRAINT_VIOLATION") is False
        assert is_retryable("AGENT_FINAL_INCORRECT") is False


class TestIsRetryableMemory:
    def test_is_retryable_memory(self):
        """MEM_* returns False."""
        assert is_retryable("MEM_CURATION_LOSS") is False
        assert is_retryable("MEM_RETRIEVAL_LOSS") is False


class TestDeterministicClassification:
    def test_deterministic_classification(self):
        """Same input produces same output."""
        error_msg = "API request timed out after 30000ms connection timeout"
        first = classify_failure(error_msg)
        second = classify_failure(error_msg)
        third = classify_failure(error_msg)
        assert first == second == third
