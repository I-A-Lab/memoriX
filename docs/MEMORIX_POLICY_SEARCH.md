# memoriX policy search

Part 23 adds deterministic bounded AutoML-style search over retention and routing policies. The selected policy is advisory and never applied automatically.

Interfaces: Python `inspect_runtime_policy_search`, CLI `tools/memorix/diagnostics/memorix_policy_search.py`, MCP `memorix_policy_search`, and OpenCode `policy_search`.

Safety: `policy_applied=false`, `runtime_modified=false`, `cold_site_accessed=false`, and `neural_model_loaded=false`. Simulations up to 6,000,000 memories are bounded by `assessment_limit`.
