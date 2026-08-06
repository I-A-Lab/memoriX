# memoriX real OpenCode A/B campaign

Part 40.7 runs the real OpenCode CLI in two isolated modes:

- `no_memory`: strict benchmark mode removes memoriX tools and disables the service;
- `memorix_core`: the actual MCP service and validated Titan hot-site memory are enabled.

The same model, prompt, scaffold and hidden tests are used for both modes. Decisions vary by seed and are not present in the prompt or project files. memoriX decisions are prevalidated to measure retrieval and use, rather than candidate review workflow.

Profiles progress from smoke to stress by increasing tasks, seeds and hard distractor memories. Every output, runtime, event stream and hidden evaluation is preserved outside the repository. A protected-source hash guard verifies that the campaign does not modify memoriX, MCP or OpenCode implementation files.

This benchmark measures end-to-end retrieval use in OpenCode. It does not use a lexical fallback or a metadata reranker.

## Part 40.7.2 reproducibility correction

- The invalid `dev_branch` subagent override was removed.
- `small`, `medium`, and `stress` require an explicit model ID.
- The default primary agent and requested model are recorded.

## Part 40.7.3 model compatibility correction

- Serious profiles may reuse the configured default model.
- This avoids forcing an installed model that cannot execute tools.
- The report records whether model selection was explicit or configured-default.
