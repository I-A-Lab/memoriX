# MEMORIX BENCHMARK OPENCODE HANDOFF

This document is the master prompt/handoff specification for the OpenCode agent tasked with implementing the new memoriX scientific benchmark harness.

## Context
You are tasked with building a robust, automated benchmark execution harness for the memoriX project. memoriX is an MCP-based persistent memory system for agents. The previous internal benchmarks (38/58 baseline vs. 58/58 memoriX) lacked sufficient volume and rigor. We are now scaling to a statistically significant, multi-seed scientific campaign.

## Your Mandate
You must implement the automation scripts, invariant guards, and data aggregators that will run these campaigns. **Do not modify the core memoriX code, and do not execute the benchmarks yet.** You are building the *infrastructure* to run them.

## Required Components to Build
Please reference `MEMORIX_BENCHMARK_IMPLEMENTATION_PLAN.md` for full architectural details. You must build:
1. **Orchestrator (`orchestrator.py`)**: Manages task queuing, seed alternation (AB/BA), and environment isolation.
2. **Invariant Guard (`invariant_guard.py`)**: Enforces strict baseline isolation (aborts if `no_memory` tries to access Titan or MCP).
3. **Aggregator & Reporter (`reporter.py`)**: Parses JSON event streams and generates the final reports as specified in `MEMORIX_BENCHMARK_REPORT_SPEC.md`.

## Critical Rules for Implementation
1. **Reproducibility is absolute:** You must enforce locked seeds, fixed API versions, and clean workspaces. (See `MEMORIX_BENCHMARK_REPRODUCIBILITY_RULES.md`).
2. **Failure Taxonomy:** Implement the strict failure classification schema (e.g., `TECH_API_TIMEOUT`, `AGENT_TOOL_HALLUCINATION`, `MEM_RETRIEVAL_LOSS`). (See `MEMORIX_BENCHMARK_FAILURE_TAXONOMY.md`).
3. **Volume Scaling:** The harness must support executing the configurations from Smoke (5 tasks) to Extreme (100k tasks). (See `MEMORIX_BENCHMARK_SAMPLE_SIZE_PLAN.md`).

## Next Steps
1. Review all Markdown files in the `docs/benchmarks/` directory.
2. Initialize the Python scripts for the Orchestrator and Invariant Guard in a new `benchmarks/src/` folder.
3. Provide an update when the basic Smoke profile infrastructure is ready for technical verification.
