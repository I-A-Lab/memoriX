# MEMORIX BENCHMARK IMPLEMENTATION PLAN

This document outlines the technical implementation plan for the OpenCode agent to construct the benchmark execution harness. 

## 1. Goal
Build a deterministic, isolated, and scalable benchmark harness that evaluates the `no_memory` and `memorix_core` (and eventually `memorix_full`) configurations without manual intervention, strictly enforcing scientific invariants.

## 2. Core Components to Build
1. **Orchestrator (`orchestrator.py`):**
   - Manages the queuing of tasks based on the Sample Size Plan.
   - Enforces the AB/BA seed alternation.
   - Provisions isolated workspace directories and empty runtime state for every run.
2. **Invariant Enforcer (`invariant_guard.py`):**
   - A wrapper that intercepts all tool calls and MCP initializations.
   - Automatically aborts and flags any `no_memory` run that attempts to load `memorix_mcp_server.py`, uses a `memory_*` tool, or accesses Titan files.
3. **Mock Validation Engine (`auto_validator.py`):**
   - Replaces the human-in-the-loop for `memory_store` candidate validation during large-scale benchmarks.
   - Follows pre-defined rules based on the dataset to either validate or reject candidates programmatically without LLM bias.
4. **Data Aggregator (`aggregator.py`):**
   - Parses the JSON event streams, extracts the failure taxonomy categories, calculates Recall@K, and prepares the data for the final report generator.
5. **Report Generator (`reporter.py`):**
   - Ingests aggregated JSON and outputs Markdown, PDF, DOCX using standard templating libraries (e.g., Jinja2, Pandoc).

## 3. Strict Guidelines for OpenCode
- **Do not modify the memoriX source code.** The benchmark harness must sit external to the project's core functionality.
- **Do not mix historical data.** The harness must generate entirely new data and not attempt to merge old results.
- **No LLM Evaluators for Binary Facts.** Use exact string matching, regex, or AST parsing for determining task success in coding tests to avoid evaluator hallucination.

## 4. Phase Delivery Sequence
1. **Phase A:** Build the Invariant Enforcer and Orchestrator. Test with the *Smoke Profile* (5 pairs).
2. **Phase B:** Build the Mock Validation Engine and execute the *Pilot Profile* (25 pairs).
3. **Phase C:** Build the Aggregator and Report Generator.
4. **Phase D:** Final validation of the harness before beginning the *Standard Profile* execution.
