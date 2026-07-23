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

The SDLC architect retrieves validated memories before requirements analysis and planning. It can reuse project conventions and prior decisions, but current user instructions always take precedence. Durable decisions are stored as pending candidates only after explicit approval.

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
8. Record the verified outcome in Project Archive.
9. Create pending memory candidates only for approved durable decisions.

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
