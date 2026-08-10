# MEMORIX BENCHMARK OPEN QUESTIONS

The following technical questions remain unresolved and must be addressed by the OpenCode agent during the harness implementation phase.

## 1. Mock Validation Engine Tuning
- **Question:** How do we programmatically simulate human validation of candidates (`memory_store`) without introducing an LLM-as-a-judge bias? 
- **Proposed Approach:** Use strict semantic similarity checks against a golden dataset of "expected facts," or explicitly bypass validation in the automated test harness by automatically promoting all candidates to Titan (only for specific benchmark slices).

## 2. Multi-Agent Shared Memory Simulation
- **Question:** How can the benchmark efficiently simulate the "Manager + Worker" shared Titan scenario without launching massive, expensive, parallel LLM swarms?
- **Proposed Approach:** Serialize the agent workflows (Manager runs, writes to Titan, terminates; Worker boots, reads from shared Titan, acts).

## 3. Token Overhead Measurement
- **Question:** How do we accurately measure token overhead introduced by memory retrieval when different model providers report usage differently?
- **Proposed Approach:** Intercept the raw prompt strings sent over the wire and run a local tokenizer (e.g., `tiktoken` for OpenAI-compatible models) to ensure standardized counting.

## 4. Extreme Capacity Latency Profiling
- **Question:** At 100,000 memories, reading the JSONL files from the disk might cause the Python MCP server to OOM or timeout during initialization. 
- **Proposed Approach:** The implementation must monitor and stream this loading process. If it OOMs, this must be caught gracefully and logged as `TECH_HOST_OOM`.
