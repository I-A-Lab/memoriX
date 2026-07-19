# memoriX retention-scoring validation

Part 21 validation covers:

- deterministic normalization and scoring;
- protected-memory behavior;
- explainable positive and risk reasons;
- deterministic hot-site ranking;
- persisted Titan metadata inspection;
- empty-runtime behavior without directory creation;
- bounded simulation through 6,000,000 memories;
- Gateway and MCP read-only contracts;
- OpenCode native tools and allow permissions;
- TypeScript type checking;
- synthetic benchmark execution;
- no runtime mutation, cold-site access, pruning, or Titan loading.

All ranking outputs include `observation_only=true`, `dry_run=true`, `applied=false`, `cold_site_accessed=false`, and `neural_model_loaded=false`.
