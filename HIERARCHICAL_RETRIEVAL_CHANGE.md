# Hierarchical Retrieval Update

Normal `memory_retrieve` now follows a trust-aware fallback hierarchy:

1. **Hot Site** — validated active Titan memories (priority 1).
2. **Short-Term Memory** — recent unvalidated events (fallback 2).
3. **Cold Site** — durable historical events (fallback 3).

## Safety rules

- The next tier is queried only when the previous tier has no relevant match.
- `project_id` and `user_id` scopes are enforced on all three participating tiers.
- STM and Cold matches expose provenance and trust metadata (`retrieval_tier`, `trust_level`, `validated`, `fallback`).
- Pending/rejected candidate objects are never queried directly.
- Cold events already associated with any candidate are excluded from normal Cold fallback, preventing candidate review, rejection, forgetting or supersession from being bypassed through raw history.
- Project Archive remains outside normal `memory_retrieve` and uses dedicated project operations.
- Cold fallback never rehydrates data into Titan automatically.
- Explicit Cold audit search remains available independently.

## Test status

Validated after the change:

- 445 non-benchmark/adaptive memory tests passed (+23 subtests).
- 124 benchmark tests passed (73 + 51 split runs).
- 22 diagnostics/release tests passed.
- Total: **591 tests passed**, plus 23 subtests.
