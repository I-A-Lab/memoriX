# memoriX — Target Architecture and Current State

## Objective

memoriX provides controlled long-term memory to the primary application and its agents, without replacing their orchestration architecture.

The Python memory is accessible only through a controlled boundary:

```text
Main Application and agents
        |
        | native tools and optional hooks
        v
memoriX TypeScript Service
        |
        | MCP JSON-RPC over stdio
        v
Python MCP Server
        |
        v
MemoriXGateway
        |
        +-- short-term memory
        +-- cold archive append-only
        +-- Project Archive append-only and versioned snapshots
        +-- pending candidates
        +-- validation or rejection
        +-- Titan active hot site
        +-- consolidation
        +-- protected nightly
        +-- adaptive observations
```

The application never directly reads or modifies the Python runtime files.

## Native Tools

- `memory_store` proposes a pending candidate;
- `memory_retrieve` searches only within active Titan memories;
- `memory_candidates_list` lists candidates by status;
- `memory_candidate_validate` validates a candidate and writes to Titan;
- `memory_candidate_reject` rejects a candidate without writing to Titan;
- `memory_consolidate` transforms short-term events into pending candidates;
- `memory_nightly_run` launches the protected nightly after confirmation;
- `memory_status` returns the state of the architecture and storage;
- `project_archive_record` adds a structured entry after confirmation;
- `project_archive_list` reads project entries;
- `project_snapshot_rebuild` adds a new snapshot version after confirmation;
- `project_snapshot_get` reads the latest snapshot.

## Retrieval Contract

Normal conversational retrieval is strictly hot-site only:

```text
memory_retrieve
    -> Titan active hot site
    -> no automatic fallback to the cold site
```

Cold search is a distinct and explicit operation:

```text
memorix_search_cold_history
    -> cold archive
    -> audit or diagnostic only
```

There is no automatic rehydration from the cold site to Titan.

## Information Lifecycle

1. An event is written to short-term memory.
2. The same event is archived directly in the cold site.
3. A candidate can be proposed explicitly or created via consolidation.
4. A pending candidate remains invisible to `memory_retrieve`.
5. Validation transforms the candidate into active Titan memory.
6. A rejected candidate does not create any Titan memory.
7. Soft-forget deactivates an active memory without deleting the cold history.

## Application Hooks

Hooks can record messages and tool results when their capture is enabled.

All memory tools and Project Archive tools are mandatory exclusions from hooks to prevent a memory operation from recording its own result.

## Project Archive

The Project Archive is an explicit cold branch, distinct from the raw history:

```text
runtime/cold_site/project_archive/
├── project_entries.jsonl
└── project_snapshots.jsonl
```

Entries and snapshots are append-only. Snapshots are deterministically rebuilt from project entries and their version increases without silent overwrites. The Project Archive is never automatically queried by `memory_retrieve`, never rehydrates Titan, and is not modified by the nightly job.

## Adaptive Memory

Available adaptive components include:

- memory pressure and pressure history;
- dynamic Topic Blocks;
- logical routing of memories;
- capacity recommendations;
- soft pruning plans;
- decisions of the adaptive controller;
- isolated synthetic benchmark.

These functions remain in observation or dry-run mode. They do not automatically modify either the hot site or the cold site.

## Live Probe

The Live Probe inspects a runtime in read-only mode. It does not load Titan, does not instantiate the gateway, does not call retrieval, and does not create any files.

## Validated Functional State

- short-term and cold recording: functional;
- pending candidates: functional;
- validation to Titan: functional;
- rejection without Titan write: functional;
- hot-only retrieval: functional;
- consolidation without automatic validation: functional;
- status tools: functional;
- read-only Live Probe: functional;
- MCP integration: functional;
- Project Archive Gateway, MCP integration: functional;
- native mutation permissions: functional;
- mandatory hook exclusions: functional;
- default runtime outside repository: functional;
- protected nightly runner, lock, and operational log: functional;
- native `memory_nightly_run` tool: functional;
- installable and verified daily Windows task: functional.

## Remaining Work

- adaptive observations fed by the real runtime;
- general transactions, migrations, and crash recovery;
- final validation of concurrency, corruption, saturation, and cross-platform compatibility.

The agent architecture remains the primary orchestration layer.

## Capacity control plane

The capacity control plane combines read-only runtime inspection, admission
control, dry-run pruning plans, a mutation lock, append-only operational logs,
MCP tools, and native application tools. Status and plan operations are read-only;
pruning is permission-gated and performs logical hot-site deactivation only.

## Memory pressure plane

The pressure plane sits between persisted hot-site metadata and future adaptive routing. It provides explainable read-only assessments and bounded aggregate reports.

## Adaptive retention ranking

Part 21 adds an observation-only ranking plane above the persisted hot-site metadata. The plane provides scores, reasons, risks, protection status, and recommended dry-run actions without altering memory state.

## Adaptive routing control plane

The control plane combines runtime capacity and retention ranking into deterministic dry-run plans.

## Deterministic policy search

The adaptive control plane includes bounded advisory policy search.

## Versioned policy lifecycle

Policy search feeds a human-governed registry with explicit activation and rollback.


## Dynamic topic blocks

See `docs/MEMORIX_TOPIC_BLOCKS.md` and `docs/MEMORIX_TOPIC_BLOCKS_VALIDATION.md`.

## Part 26 - controlled consolidation

memoriX now supports reviewed consolidation plans, local session state, scheduling, recovery, MCP, and application integration.

## Part 27 - Observability

Bounded diagnostics, snapshots, alerts, drift comparison, and continuous evaluation are available without loading Titan or mutating memory policies.
## Release and operator layer

The final operator layer provides readiness inspection, portable hashed runtime archives, atomic restore, a PowerShell command installer, and an isolated end-to-end smoke scenario without expanding the LLM-facing tool surface.
