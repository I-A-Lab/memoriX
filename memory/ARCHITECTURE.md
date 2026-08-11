# memoriX Python Memory Architecture

## Current implementation status

memoriX is an operational external-memory system connected to OpenCode.

The current implementation includes:

- a Python gateway coordinating all memory operations;
- a Python MCP server using JSON-RPC over stdio;
- an isolated TypeScript MCP client and service;
- native OpenCode tools for storing, retrieving, reviewing and consolidating memory;
- optional OpenCode hooks for recording messages and tool results;
- a Titan neural hot site containing human-validated active memories;
- a durable cold archive containing the complete event history;
- an explicit append-only Project Archive with versioned snapshots;
- candidate validation and rejection workflows;
- adaptive observation and dry-run components;
- read-only diagnostics through the Live Probe;
- protected nightly consolidation with locking and operational journals;
- native OpenCode nightly execution and Windows Task Scheduler integration.

## Core memory contract

```text
OpenCode event or explicit memory request
                |
                v
          short-term memory
                |
                +--------------------> cold durable archive
                |
                v
         Titan V2 consolidation
                |
                v
          pending candidates
                |
         explicit validation
                |
                v
          Titan active hot site
                |
                v
          hierarchical retrieval
```

The non-negotiable architectural rules are:

- short-term events are archived directly in the cold site;
- the cold site is complete durable audit history;
- validated candidates are stored in the hot site only;
- normal retrieval uses a recency-first hierarchy: Short-Term Memory first, then Hot Site, then Cold Site as a final fallback;
- explicit cold history search remains available for audit;
- normal retrieval falls back to Cold Site only after Short-Term Memory and Hot Site miss;
- Cold fallback never rehydrates archived events into Titan;
- there is no automatic cold-to-hot rehydration;
- pending and rejected candidates are not available to retrieval;
- update and soft-forget operations affect the hot site only;
- pruning must never alter the cold archive;
- consolidation may create pending candidates but must never validate them automatically.

## Package responsibilities

### `gateway`

Public Python boundary coordinating storage, retrieval, candidate lifecycle, consolidation, nightly operations and status reporting.

### `hot_site/short_term_memory`

Stores recent events before consolidation. Every recorded event is also archived directly in the cold site.

### `hot_site/titan_active_memory`

Stores human-validated active memories and serves as the second, validated tier of normal retrieval after STM.

### `cold_site/long_term_store`

Stores append-only durable event history used both for explicit audit and as the final, provenance-labelled fallback tier when Short-Term Memory and Hot Site have no relevant match.

### `cold_site/project_archive`

Stores explicit append-only project entries and append-only versioned snapshots. Project Archive is cold, audit-oriented and never participates in automatic retrieval or Titan rehydration.

```text
runtime/cold_site/project_archive/
├── project_entries.jsonl
└── project_snapshots.jsonl
```

### `consolidation`

Scores, groups and summarizes short-term events into pending memory candidates.

### `sync`

Contains protected nightly consolidation and active hot-site replay logic.

### `adaptive`

Provides pressure observations, dynamic Topic Blocks, capacity recommendations, pruning plans and controller decisions. Actions remain observation-only or dry-run.

### `diagnostics`

Provides bounded runtime-file inspection and the read-only Live Probe.

Observability reports, snapshots, alerts and drift analysis live under
`adaptive/observability.py` and `adaptive/observability_history.py`. Benchmark
reporting remains isolated under `benchmark`.

### `integrations/mcp`

Exposes the gateway through controlled MCP tools. OpenCode never writes directly to Python storage files.

## OpenCode integration

The native OpenCode memory tools are:

- `memory_store`;
- `memory_retrieve`;
- `memory_candidates_list`;
- `memory_candidate_validate`;
- `memory_candidate_reject`;
- `memory_consolidate`;
- `memory_nightly_run`;
- `memory_status`;
- `project_archive_record`;
- `project_archive_list`;
- `project_snapshot_rebuild`;
- `project_snapshot_get`.

The OpenCode hooks are optional and disabled unless configured. Memory and Project Archive tools are mandatory exclusions from hook capture to prevent self-recording loops. Mutating Project Archive tools require native OpenCode approval.

## Runtime isolation

Runtime state is selected through `MEMORIX_RUNTIME_ROOT` or the launcher parameter `RuntimeRoot`.

Tests and manual validation must use a runtime outside the repository. Default runtime resolution is platform-aware and remains outside the source repository.

## Remaining work

- connect adaptive observation to production runtime data;
- add broader transactions, recovery and migrations;
- complete concurrency, corruption, saturation and cross-platform testing.

## Capacity boundary

Titan active memory is a bounded hot site. Admission is checked before
candidate validation writes. At exhaustion, the candidate remains pending.
Soft pruning can deactivate eligible hot memories only after an explicit
dry-run plan and operator approval. The cold archive is never pruned.

## Memory pressure observation

Persisted Titan metadata is converted into normalized per-memory pressure inputs without loading the neural model or consulting the cold site. The resulting status is observational only.

## Adaptive retention ranking boundary

The adaptive retention layer reads persisted Titan metadata and produces ranked assessments only. It is isolated from mutation, cold-site history, automatic rehydration, and neural-model loading.

## Adaptive routing boundary

Adaptive routing is a planning layer only. It does not mutate Titan or the cold site.

## Policy-search control plane

Policy search is observation-only and never mutates the memory data plane.

## Policy lifecycle registry

The policy lifecycle registry is separate from Titan memory data and records versioned control-plane state.


## Dynamic topic-block control plane

See `docs/MEMORIX_TOPIC_BLOCKS.md` and `docs/MEMORIX_TOPIC_BLOCKS_VALIDATION.md`.

## Part 26 - controlled consolidation

memoriX now supports reviewed consolidation plans, local session state, scheduling, recovery, MCP, and OpenCode integration.

## Part 27 - Observability

Bounded diagnostics, snapshots, alerts, drift comparison, and continuous evaluation are available without loading Titan or mutating memory policies.
## Final release boundary

Release-readiness, runtime backup/restore, and the isolated demo smoke test live under `memory/release`. These operator controls are intentionally not exposed as MCP tools: restore and launcher installation require explicit local administration.
