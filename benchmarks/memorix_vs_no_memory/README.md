# memoriX versus No Memory Benchmark

This directory contains the reproducible benchmark comparing OpenCode/SDLC without persistent memoriX memory against controlled memoriX configurations.

## Part 29 status

Part 29 defines contracts only. It does not change OpenCode registration, prompts, plugins, MCP startup, Titan, or runtime behavior.

The official initial modes are:

- `no_memory`: strict baseline with no memoriX tool, prompt, plugin, MCP process, runtime, Titan, cold site, candidate, consolidation, adaptive policy, or Project Archive;
- `memorix_core`: persistent memory, Titan, cold site, candidates, retrieval and Project Archive, without consolidation, adaptive routing or active policy;
- `memorix_full`: complete memoriX configuration with consolidation, adaptive routing, active policy and plugin capture.

Part 30 must make these contracts executable and prove that `no_memory` is isolated.

## Scientific rules

Paired executions must use the same commit, task, dataset, prompt version, model and model parameters, budgets, timeout, hardware, seed and evaluator version. Execution order alternates between modes. Every run has an isolated runtime. Failed runs remain in immutable raw results.

## Configuration files

- `configs/configurations.json`: mode and fairness contracts;
- `configs/metrics.json`: primary metrics by benchmark suite;
- `configs/sizes.json`: bounded dataset sizes.

Validate them with:

```powershell
py -3.10 ".\tools\memorix\research\memorix_benchmark_contracts.py"
```

## Run manifests

Every execution will be preceded by an immutable manifest containing the complete
request and environment snapshot. See `docs/MEMORIX_BENCHMARK_MANIFESTS.md`.
The manifest layer does not execute a benchmark and does not create a repository
runtime.
## Deterministic datasets

Part 32 adds versioned JSONL datasets with fixed seeds, official data families,
retrieval queries and SHA-256 integrity manifests. Generated datasets must be
written outside the repository during validation and benchmark execution.

## Part 33 - Pure-memory benchmark

The pure-memory suite evaluates retrieval quality and latency independently from the agent and SDLC layers. It supports a deterministic lexical control engine and the real memoriX gateway. Generated datasets and results remain outside the repository during development.

## Part 34: System instrumentation

Part 34 records wall time, process RSS, CPU usage, timeout status, stdout/stderr fingerprints, and tracked runtime-directory growth for benchmark subprocesses. Reports are generated outside the repository and can embed the corresponding memory-pure benchmark report.
## Part 35 - Agent multi-session benchmark

`memorix_agent_multisession_benchmark.py` compares a session-only `no_memory` agent with `memorix_core` across a forced session boundary. Detailed outputs are written outside the repository.

## Part 36: SDLC benchmark

The SDLC benchmark compares `no_memory` and `memorix_core` across project creation and a new-session requirement change. Detailed reports are generated outside the repository.

## Part 37: ablation benchmark

The ablation suite isolates the contribution of persistence, consolidation, routing, Project Archive, and multi-agent coordination.

## Part 38: load and robustness

The load and robustness suite measures bulk storage, corruption recovery, restart behavior, timeout enforcement, restoration, and near-capacity protection.

## Part 39: multi-seed orchestration

The multi-seed orchestrator repeats benchmark suites, stores one report per seed and mode, supports resume, and computes descriptive statistics with 95% confidence intervals.

## Part 40: final report generation

The final-report generator converts multi-seed results into CSV, JSON, chart-ready data, and a Markdown benchmark summary.

## Part 40.5: real reference campaign

The real reference campaign executes the actual memoriX gateway across distinct seeded datasets, preserves all raw artifacts and runtimes, and creates an analysis ZIP.

## Part 40.6: retrieval diagnostic

The retrieval diagnostic separates raw Titan quality from metadata-aware hybrid retrieval and evaluates negative queries by exclusion.

## Part 40.7: real OpenCode A/B campaign

The graduated real campaign runs the actual OpenCode CLI with identical hidden functional tasks in strict `no_memory` and real `memorix_core` modes. It preserves outputs and verifies protected source hashes before and after execution.

## Part 40.8: resilient real OpenCode campaign

The resilient campaign adds retries, checkpoints, resume support, valid-pair
aggregation, and strict final validation before running large or stress profiles.

## Part 41: real dynamic memory lifecycle

The dynamic lifecycle campaign tests real creation, update, replacement,
restart persistence, project isolation, soft-forget, consolidation, duplicate
prevention, and cold-history persistence without calling an LLM.

## Part 42: tenant and contradiction audit

This diagnostic campaign separates storage lifecycle correctness from
retrieval namespace precision and strict cross-user/cross-project isolation.
It always preserves and archives completed audit results, including warnings.
