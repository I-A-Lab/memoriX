# memoriX adaptive-routing validation

Validation covers empty runtimes, pending candidates, protected memories, saturated simulations up to 6,000,000 memories, MCP/OpenCode exposure, deterministic dry-run plans, and bounded benchmarks.

Required invariants: `dry_run=true`, `applied=false`, `candidate_validated=false`, `pruning_executed=false`, `runtime_modified=false`, `cold_site_accessed=false`, and `neural_model_loaded=false`.
