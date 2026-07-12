# memoriX Python Memory Architecture

## Current integration phase

This directory is the Python foundation for the memoriX external-memory
system.

At this stage:

- no OpenCode integration is enabled;
- no MCP server is enabled;
- no OpenCode hook calls the Python memory;
- no production memory event is written;
- Antoine's existing `memory/titan_model.py` is preserved unchanged.

## Target memory contract

    short-term memory
            |
            +------------------> cold site durable history
            |
            +------------------> Titan V2 consolidation
                                       |
                                       v
                                memory candidates
                                       |
                                human validation
                                       |
                                       v
                                hot site Titan

The architectural rules are:

- short-term events are archived directly in the cold site;
- the cold site is a complete durable history;
- validated candidates are stored in the hot site only;
- active retrieval uses the hot site only;
- cold history search is explicit and audit-only;
- there is no automatic cold-site fallback;
- there is no automatic cold-to-hot rehydration;
- updates and soft-forget affect only the hot site;
- pruning must never alter the cold archive.

## Package responsibilities

### `gateway`

The future public Python entry point.

It will coordinate memory operations without exposing storage internals.

### `hot_site/short_term_memory`

Recent events received by the memory system.

This package will eventually contain:

- recent event models;
- short-term event storage;
- event loading;
- event cleanup after successful consolidation.

### `hot_site/titan_active_memory`

Curated, validated, active memories available to retrieval.

This package will eventually contain:

- the active Titan backend;
- validated-memory storage;
- active retrieval;
- update handling;
- hot-site-only soft-forget.

### `cold_site/long_term_store`

Complete durable event history for audit and debugging.

The cold site must:

- receive short-term events directly;
- preserve the raw historical record;
- remain independent from candidate validation;
- remain independent from hot-site pruning;
- never be used as an automatic retrieval fallback.

### `cold_site/project_archive`

Explicit project-level archival operations.

These operations must remain separate from active-memory retrieval.

### `consolidation`

Short-term processing components.

This package will eventually contain:

- importance scoring;
- confidence scoring;
- surprise scoring;
- event grouping;
- deterministic or model-assisted summaries;
- update detection;
- memory-candidate creation.

Consolidation must never write validated memories directly into the cold site.

### `sync`

Replay and synchronization operations restricted to the active hot-site path.

Nightly synchronization must:

- process the short-term to hot-site path;
- replay active validated memories when required;
- produce execution logs;
- verify that the cold site was not modified.

### `data`

Shared domain models and storage contracts.

This package will eventually contain models such as:

- short-term events;
- archived events;
- memory candidates;
- validated memories;
- retrieval results;
- update and forgetting metadata.

### `observability`

Metrics, diagnostics, benchmark support, and live-probe support.

This package will eventually contain:

- momentum;
- entropy;
- surprise;
- memory pressure;
- topic-block diagnostics;
- benchmark reports;
- live-probe reports.

## Important boundaries

The Python memory package must remain independent from OpenCode during this
phase.

OpenCode and MCP will be integrated only after the Python memory components
have their own passing tests.

OpenCode must never write directly into Python memory-storage files.

Future communication must pass through a controlled integration boundary,
such as the memoriX gateway exposed through MCP.

## Current implementation status

At the end of this initial skeleton phase:

- package directories exist;
- Python packages are importable;
- the architecture contract is documented;
- Antoine's Titan prototype remains unchanged;
- no memory backend has been activated;
- no storage file has been created;
- no OpenCode source file has been modified.
