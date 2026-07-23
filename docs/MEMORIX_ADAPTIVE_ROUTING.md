# memoriX adaptive routing

Part 22 combines hot-site capacity, adaptive retention ranking and bounded soft-pruning candidates into an explainable dry-run routing plan.

Decisions include `admit`, `admit_after_pruning`, `defer`, `protect`, `keep`, `reject_safely` and `review_for_soft_pruning`.

The runtime adapter, CLI, MCP tool `memorix_adaptive_routing_plan`, and OpenCode tool `adaptive_routing_plan` never mutate Titan, validate a candidate, execute pruning, access the cold site, or load the neural model.
