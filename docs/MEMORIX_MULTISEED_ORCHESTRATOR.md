# memoriX multi-seed orchestrator

Part 39 adds repeatable multi-seed execution and aggregation.

The orchestrator currently runs the deterministic SDLC suite for
`no_memory` and `memorix_core`. It records every run separately and
aggregates mean, median, standard deviation, range, and a normal
approximation 95% confidence interval.

The `--resume` flag reuses completed and validated runs. Generated runs
and reports must remain outside the repository.
