
# memoriX policy lifecycle

Part 24 introduces a versioned registry for memory policies. AutoML proposes a policy, a human explicitly approves or rejects it, and activation is a separate operation. The registry stores immutable policy versions in `policies/policy_versions.jsonl` and current state in `policies/policy_state.json` using atomic replacement.

## Operations

`inspect`, `propose`, `approve`, `reject`, `activation_plan`, `activate`, `rollback_plan`, and `rollback` are exposed through `memorix_policy_lifecycle` and OpenCode `policy_lifecycle`.

Approval is not activation. Activation requires an approved version and a non-empty validation identifier. Rollback restores the previous version without deleting history. No operation loads Titan or accesses the cold site.
