# MEMORIX PROJECT MASTER SUMMARY

## 1. Introduction and Architecture Overview
memoriX provides a controlled, persistent, and long-term memory system for OpenCode and its agents. It is designed to run alongside the standard orchestration architecture without replacing it. 

### Core Architecture Flow
```text
OpenCode and agents
        |
        | Native tools & optional hooks
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
        +-- Short-term memory (append-only)
        +-- Cold archive (append-only)
        +-- Project Archive (append-only & versioned snapshots)
        +-- Pending candidates
        +-- Validation or rejection workflow
        +-- Titan active hot site (Retrieval source)
        +-- Consolidation mechanisms
        +-- Nightly protected tasks
        +-- Adaptive observations
```

## 2. Key Modules and Components

### 2.1 Native Tools Exposed to OpenCode
OpenCode interacts with memoriX purely via the following tools:
- `memory_store`: Proposes a candidate memory awaiting human validation.
- `memory_retrieve`: Searches explicitly within the active Titan hot site.
- `memory_candidates_list`: Lists memories waiting for validation.
- `memory_candidate_validate`: Approves a candidate and commits it to the Titan hot site.
- `memory_candidate_reject`: Rejects a candidate.
- `memory_consolidate`: Transforms short-term events into pending candidates.
- `memory_nightly_run`: Triggers nightly maintenance operations.
- `memory_status`: Returns system and capacity status.
- `project_archive_record`: Appends structured entries to the project archive.
- `project_archive_list`: Lists project archive entries.
- `project_snapshot_rebuild`: Deterministically rebuilds a project snapshot.
- `project_snapshot_get`: Reads the latest snapshot.

### 2.2 Short-term Memory, Cold Site & Project Archive
Every event is logged to **short-term memory** and directly archived into a **cold site** (append-only). 
The **Project Archive** is a specific, explicitly written cold branch that manages versioned snapshots of a project. 
**Important Invariant**: The cold site is never automatically queried during a standard conversational retrieval (`memory_retrieve`). There is no automatic rehydration of the cold site into the Titan hot site.

### 2.3 Candidates and Human Validation
To ensure memory quality, any new explicit memory undergoes a validation lifecycle:
1. Candidate proposed via `memory_store`.
2. Resides in `pending_review` (invisible to retrieval).
3. Requires explicit validation via `memory_candidate_validate` to enter the Titan hot site.

### 2.4 Retrieval and Hot-Titan
Retrieval relies entirely on the **Titan hot site**. Hot-Titan dimensions use a standard `d_model=256`, operating primarily on CPU. Retrieval is guaranteed to only search active memories and will not fall back to cold storage.

### 2.5 Supersession and Omission (Soft-forget)
Memory updates involve targeted supersession. Soft-forget operations logically deactivate an active memory from the hot site while retaining its history in the cold archive. No active item is silently evicted.

### 2.6 Dynamic Topic Blocks
Topic blocks act as logical routing metadata, heavily reliant on canonical tags to avoid lexical fragmentation. Without tags, memory routing fragments around dominant words; with tags, routing is deterministic and reliable.

### 2.7 Capacity and Elastic Expansion (Phase 2A5)
memoriX maintains a `baseline_capacity` and `current_capacity`.
- Overflows are blocked; a candidate remains pending rather than overwriting.
- Elastic expansion triggers according to: `max(current + minimum_growth, ceil(current * 1.25), item_count + required_slots)`.
- Reverting to baseline capacity occurs only if `active_count <= floor(baseline_capacity * 0.80)`.

### 2.8 Nightly Consolidation and Maintenance
A protected nightly runner handles consolidation, pruning, consistency checks before compaction, and soft-forget limits. It ensures the memory database remains optimized and coherent.

### 2.9 Isolation and Security
- **Tenant/Project Isolation**: Memories are strictly scoped by project and user ID to prevent cross-contamination.
- **Hook Exclusions**: All `memory_*` and `project_archive_*` tools must be excluded from automated LLM hooks to prevent recursive memory capture loops.

## 3. Risks and Benchmarking Focus
- **Tool Hallucination**: The LLM inventing memory tools or parameters.
- **Retrieval Bottlenecks**: Fragmentation of topic blocks and failure to recall distant facts.
- **Capacity Boundaries**: Correct behavior when capacity is full (graceful degradation without silent deletion).
- **Contamination**: Verifying tenant/project isolation is strictly respected.
