# MEMORIX BENCHMARK FAILURE TAXONOMY

To prevent manual, subjective interpretation of errors, all failures encountered during the benchmark campaigns will be strictly categorized according to this taxonomy.

## 1. Technical Infrastructure Failures (Retry Allowed)
These are failures outside the scope of the experimental variables and trigger an automatic retry.
- **`TECH_API_TIMEOUT`**: Model provider failed to respond within the configured timeout.
- **`TECH_API_AUTH`**: HTTP 401 or 403 provider authentication errors.
- **`TECH_HOST_OOM`**: Out-of-memory exception on the host OS running the benchmark.
- **`TECH_MCP_CRASH`**: Unhandled exception leading to the crash of the Python MCP server.

## 2. Agent Logic Failures (No Retry)
These represent failures in the LLM's reasoning or execution and are counted as scientific results.
- **`AGENT_TOOL_HALLUCINATION`**: The agent attempts to call a tool that does not exist or uses an invalid schema (e.g., calling `memorix_search_cold_history` instead of `memory_retrieve`).
- **`AGENT_BASH_RECOVERY_FAIL`**: The agent executes an invalid bash command and fails to self-correct after receiving the error stderr.
- **`AGENT_LOGIC_LOOP`**: The agent repeats the exact same sequence of tool calls more than 3 times without progressing.
- **`AGENT_CONSTRAINT_VIOLATION`**: The agent uses forbidden information or fails to satisfy a hidden test constraint.
- **`AGENT_FINAL_INCORRECT`**: The agent successfully completes the run but provides an incorrect final answer.

## 3. Memory Pipeline Failures (No Retry)
These failures isolate where the memoriX pipeline broke down.
- **`MEM_CURATION_LOSS`**: The required information was never proposed via `memory_store` or `memory_consolidate`.
- **`MEM_VALIDATION_LOSS`**: A candidate was proposed but failed to validate or was rejected incorrectly.
- **`MEM_RETRIEVAL_LOSS`**: The information is in Titan, but `memory_retrieve` failed to surface it (e.g., due to lexical fragmentation without canonical tags).
- **`MEM_ANSWER_LOSS`**: The information was successfully retrieved into context, but the LLM failed to incorporate it into its final action/answer.
- **`MEM_SILENT_EVICTION`**: A memory was logically expected to be in the hot-site but was incorrectly removed (should theoretically be 0 based on Phase 2A5 invariants).
