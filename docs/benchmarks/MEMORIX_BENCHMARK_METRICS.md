# MEMORIX BENCHMARK METRICS

The benchmark will measure multiple dimensions, clearly separating capability improvements from system overhead.

## 1. Primary Quality Metrics
These metrics determine if the memory system successfully influences the agent's behavior.
- **Task Success Rate:** Binary completion of the core prompt objective.
- **Hidden Constraint Compliance:** Success rate on non-prompted edge cases (verified by hidden tests).
- **Correction Steerability:** Rate at which the agent recovers from a failure when provided with feedback from memory.

## 2. Memory Retrieval Metrics
These metrics isolate the performance of the Titan hot-site retrieval engine.
- **Curation Rate:** % of cases where the required reference was correctly stored into the pending candidate pool.
- **Validation Rate:** % of cases successfully transitioned from candidate to hot-site Titan.
- **Recall@1, Recall@5:** The presence of the required memory in the top-K retrieved results.
- **Mean Reciprocal Rank (MRR):** The position of the correct memory in the retrieved context.
- **Distractor Intrusion Rate:** % of retrieved memories that are entirely irrelevant.

## 3. System Cost Metrics
These metrics quantify the overhead introduced by the memoriX architecture.
- **Execution Duration:** Total wall-clock time per task (Baseline vs. memoriX).
- **Memory Tool Latency:** Specifically measuring time spent in `memory_retrieve`, `memory_store`, and `memory_consolidate`.
- **Token Overhead:** Extra input tokens consumed by retrieved memories and tool schemas.
- **Tool Call Count:** Difference in average number of tool calls required to complete a task.

## 4. Resource Utilization
- **Peak RSS:** Maximum RAM consumption of the Python runtime and MCP server.
- **Storage Size:** Disk footprint in MiB of the `short_term`, `cold_site`, and `titan_db` directories.
- **Restart Latency:** Time taken to hydrate the Titan database from disk on MCP server startup.
