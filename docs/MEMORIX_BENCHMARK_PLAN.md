# memoriX Global Benchmark Plan

## 1. Objective

The benchmark must determine whether persistent memoriX memory improves OpenCode/SDLC quality, in which scenarios, and at what cost in latency, tokens, RAM and disk usage. Results must expose regressions and failure cases as well as gains.

## 2. Scope

Five suites remain separate:

1. memory: deterministic storage, retrieval, update, forget, contradiction and contamination tests;
2. agent: multi-turn and multi-session information reuse;
3. SDLC: project creation, evolution, bug correction and session resume;
4. system: latency, CPU, RAM, MCP startup and storage growth;
5. robustness: saturation, corruption, timeout, restart and restoration.

A single aggregate score is not authoritative. Quality and cost are reported separately.

## 3. Initial configurations

### `no_memory`

This is the scientific baseline. It must expose no memoriX tools, load no memoriX plugin or memory-specific prompt, start no memoriX MCP server, create no memoriX runtime and access neither Titan nor Project Archive.

### `memorix_core`

This enables persistent memory, Titan, cold storage, candidates, retrieval and Project Archive. Consolidation, adaptive routing and active policies remain disabled so that the value of the core memory path can be measured.

### `memorix_full`

This enables the complete supported memoriX path, including consolidation, adaptive routing, active policy and plugin capture.

Additional ablations are introduced only after the three primary modes are executable and validated.

## 4. Fairness contract

Within each paired comparison, the following values are identical and recorded:

- Git commit;
- task and dataset identifiers;
- prompt version outside controlled memory sections;
- model identifier and generation parameters;
- tool, turn and timeout budgets;
- hardware identifier;
- random seed;
- evaluator version.

Execution order alternates by seed. Each run uses an isolated runtime directory. Raw successful and failed runs are retained without in-place editing.

## 5. Baseline invariants

Part 30 must automatically fail a `no_memory` run if any of these conditions is observed:

- a `memory_*` or `project_archive_*` tool is exposed or called;
- a memoriX plugin or hook is loaded;
- an agent prompt contains an active memoriX instruction;
- `memorix_mcp_server.py` is started;
- a memoriX runtime file is created;
- Titan, cold site, candidates, consolidation, adaptive routing or active policy is accessed.

## 6. Primary metrics

Memory quality prioritizes Recall@1, Recall@5, MRR, false-memory rate, stale-memory rate, update and forget success, and cross-user or cross-project contamination.

Agent and SDLC quality prioritizes task completion, test success, constraint compliance, reuse of prior validated information, forbidden-information use, regressions, corrections, turns and tool calls.

System cost prioritizes startup, store, retrieve, validation and consolidation latency, peak RSS, CPU and hot/cold/runtime disk size.

Robustness prioritizes successful execution, timeout containment, malformed-record recovery, restart recovery, archive restoration and capacity rejection accuracy.

## 7. Volume profiles

The versioned profiles are:

- tiny: 10 memories, 20 distractors;
- small: 100 memories, 100 distractors;
- medium: 1,000 memories, 2,000 distractors;
- large: 10,000 memories, 20,000 distractors;
- stress: 50,000 memories, 100,000 distractors;
- extreme: 100,000 memories, 250,000 distractors.

Only tiny, small and medium may run automatically at first. Large, stress and extreme require explicit execution. Extreme is always manual.

## 8. Result policy

No final performance value may be committed before a real run. Every report must include configuration, environment, raw run identifiers, failures, limitations and the exact aggregation method. Historical benchmark values are context only and are not reused as final evidence.

## 9. Delivery sequence

- Part 29: contracts, documented configurations and validation tests;
- Part 30: executable strict baseline and feature gates;
- Part 31: run manifests and result schemas;
- Part 32: deterministic datasets;
- Part 33: pure-memory benchmark;
- Part 34: system instrumentation;
- Part 35: agent benchmark;
- Part 36: SDLC benchmark;
- Part 37: ablations;
- Part 38: load and robustness;
- Part 39: statistical aggregation;
- Part 40: reports and charts;
- Part 41: README integration and final validation.

## 10. Part 29 exit criteria

Part 29 is complete only when:

- all three JSON configuration files parse and validate;
- the strict `no_memory` contract rejects every enabled memory feature;
- core and full modes remain distinct;
- all six bounded size profiles exist and extreme is manual;
- all five metric groups are non-empty;
- targeted unit tests pass;
- the full memoriX verification still passes;
- no runtime or generated benchmark result is added to the repository.
