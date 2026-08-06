# memoriX SDLC and Memory Integration

## Purpose

This integration combines Antoine's latest SDLC agent behavior with Elwen's validated memoriX external-memory stack.

## Agent availability

Memory is not tied to the `build` agent. OpenCode's native tool registry is shared by the primary and subagent modes. The following agents can receive memory tools:

- `build`
- `sdlc`
- `dev_branch`
- `test_branch`

Actual execution remains governed by the merged permission rules in `.opencode/opencode.jsonc`.

## Memory behavior by agent

### build

The build agent can use the complete memoriX workflow, including controlled candidate creation, human validation, retrieval, Project Archive, consolidation, capacity, policies, topic blocks, and observability.

### sdlc

The SDLC architect retrieves validated memories before requirements analysis and planning. It can reuse project conventions and prior decisions, but current user instructions always take precedence. After a successful final validation gate, it automatically proposes one deduplicated pending candidate for the verified milestone. Candidate validation remains an explicit human action.

### dev_branch and test_branch

The implementation and test subagents use memory in read-only mode. They may retrieve validated project context but must not create, validate, reject, or consolidate memories autonomously.

## Final SDLC lifecycle

1. Retrieve validated project memory.
2. Clarify requirements when required.
3. Produce and approve PRD/SRS.
4. Produce and approve development and test plans.
5. Produce and approve the detailed atomic plan.
6. Delegate implementation and tests in parallel.
7. Run the targeted validation gate.
8. If validation succeeds, inspect the current Project Archive and pending/validated memories for an equivalent milestone.
9. Record exactly one verified milestone in Project Archive when no equivalent entry exists.
10. Create exactly one pending memory candidate when no equivalent candidate or validated memory exists.
11. Report the pending candidate identifier; never validate or reject it automatically.

## Merge rules

The following Antoine artifacts are integrated:

- latest `sdlc`, `dev_branch`, and `test_branch` prompts;
- desktop development and packaging commands;
- desktop distribution documentation.

The following artifacts are intentionally not copied:

- `.coverage` and Python bytecode;
- `.opencode/memory/titan_store.json`;
- generated PRD and plan files from Antoine's demonstration;
- Antoine's memory-less tool registry and empty permission map.

Elwen's Python memory implementation, MCP server, native OpenCode memory tools, permissions, tests, release tooling, and documentation remain authoritative.


## Automatic final-milestone persistence

The final persistence sequence is intentionally implemented in the OpenCode SDLC agent rather than in the Titan backend. The agent has the semantic context needed to know whether implementation and tests actually completed successfully; the storage backend does not.

The repository configuration allows `memory_store` and `project_archive_record` so the SDLC agent can create the archive entry and pending candidate without an extra manual request. `memory_candidate_validate` and `memory_candidate_reject` remain confirmation-gated.

Project Archive provenance is mandatory. For a new verified milestone, `memory_store` runs before `project_archive_record`, because its result exposes the real short-term `eventID` and pending `candidateID`. The archive call then uses that event ID in a non-empty `source_event_ids` array. When an equivalent candidate already exists, the agent reuses its existing `source_event_ids`. Current OpenCode session, message, or subagent session IDs are only a last-resort provenance reference when no real event ID is exposed. The agent must never make an incomplete first archive call and retry only after validation fails.

The sequence must be idempotent:

- no candidate at project creation time;
- no candidate after a failed or incomplete validation gate;
- one archive milestone per verified outcome;
- one pending candidate per verified outcome;
- no automatic Titan validation;
- retries or resumed summaries must reuse an existing equivalent entry or candidate.
