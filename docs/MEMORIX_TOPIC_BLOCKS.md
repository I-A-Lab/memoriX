# memoriX dynamic topic blocks

Part 25 adds versioned logical topic blocks, deterministic detection, controlled creation, aliases, routing assignments, merge history, archive/restore, and dry-run rebalance plans. Mutation tools require explicit permission. Protected blocks cannot be archived or merged as a source. The general block may be configured as the default. No operation accesses the cold site or loads Titan.

MCP tool: `memorix_topic_blocks`. OpenCode tool: `topic_blocks`.
