# Strict no-memory baseline

Set `MEMORIX_BENCHMARK_MODE=no_memory` to activate the scientific baseline.

The mode forces the memoriX service off, removes native memoriX and project archive tools from the tool registry, turns the memoriX plugin into a no-op, and strips memoriX-specific sections from SDLC prompts. It must not create or connect to a memoriX runtime.

`MEMORIX_ENABLED=true` cannot override this strict mode.
