# memoriX tenant and contradiction audit

Part 42 is a diagnostic benchmark using the real public Python gateway and
the real Titan hot site. It does not call OpenCode, MCP, an LLM, or a remote
provider.

The audit deliberately stores near-identical and contradictory memories for
multiple users and projects. It separates three questions:

1. Storage lifecycle:
   - validated records are present and active;
   - replacement deactivates only the stale target;
   - version and supersedes lineage are correct;
   - restart persistence is correct;
   - forgetting one tenant leaves other tenant records active.

2. Retrieval namespace precision:
   - exact and paraphrased user queries return the correct top result;
   - project-specific queries return the correct top result;
   - a replacement is retrieved instead of its stale version;
   - forgotten memories remain absent after restart.

3. Strict isolation:
   - no foreign user memory appears in top-k;
   - no foreign project memory appears in top-k;
   - the gateway exposes explicit project_id and user_id retrieval filters.

This is an audit, not a pass-only campaign. A ZIP is produced whenever the
campaign completes and protected source files remain unchanged, even if the
audit discovers retrieval or isolation warnings.

Profiles:

- quick: 2 seeds, 4 users, 3 projects, 50 distractors;
- standard: 3 seeds, 8 users, 4 projects, 250 distractors.
