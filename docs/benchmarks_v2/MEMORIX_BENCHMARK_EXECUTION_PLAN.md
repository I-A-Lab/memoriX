# MEMORIX BENCHMARK EXECUTION PLAN

This document dictates the operational sequence for executing the benchmark campaigns once the harness is built.

## 1. Pre-Flight Checklist
- Ensure the test environment has a stable network connection to the required API provider.
- Disable all background tasks, indexing services, and virus scanners that might introduce I/O latency anomalies on the host machine.
- Generate cryptographic hashes (SHA-256) of the OpenCode source, memoriX source, and benchmark datasets. Record these in the run manifest.

## 2. Profile Execution Order
Executions must strictly follow this escalating sequence to avoid wasting API budgets on broken harnesses:

1. **Smoke Run:** Run 5 pairs. Manually review the output JSON logs to verify invariant enforcement and proper data schema formatting.
2. **Pilot Run:** Run 25 pairs. Analyze the failure taxonomy distribution. If `TECH_` errors exceed 5%, abort and investigate the API provider or network stability.
3. **Standard Run:** Run 150 pairs overnight. 
4. **Large Run:** Run 500 pairs. This must be scheduled during the weekend to ensure no other load exists on the host machine.
5. **Research Runs:** Trigger specific subsets (e.g., Multi-agent shared Titan, Extreme Capacity) manually.

## 3. Data Retention and Cleanup
- Every run must execute in a dynamically generated, isolated workspace (e.g., `/tmp/memorix_run_<uuid>`).
- Upon completion (success or failure), the entire workspace, `short_term` events, and `titan_db` must be zipped, hashed, and moved to a persistent cold storage archive.
- The original uncompressed directories must be deleted to prevent disk saturation during the Large and Research profiles.

## 4. Abort Procedures
- If the `invariant_guard.py` triggers more than 3 times in a single profile, the execution must be paused immediately. This indicates a structural failure in the prompt isolation or tool schema mapping.
- If memory pressure on the host exceeds 90% (due to Titan loading in Extreme capacity profiles), the orchestrator must gracefully kill the Python MCP server and log a `TECH_HOST_OOM` error.
