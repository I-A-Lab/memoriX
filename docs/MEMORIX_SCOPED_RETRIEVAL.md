# Scoped retrieval

Part 43 adds optional exact `project_id` and `user_id` filters to active
Titan retrieval. Candidate Titan item IDs are restricted from validated
metadata before neural scoring and ranking.

Omitting both filters preserves the previous global retrieval behavior. The
filters are also exposed by the `memorix_context` MCP tool.

The Part 42 audit is upgraded to version 42.1.0 and now executes all tenant
and project checks through the scoped retrieval contract.
