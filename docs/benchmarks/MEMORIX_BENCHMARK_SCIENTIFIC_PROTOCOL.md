# MEMORIX BENCHMARK SCIENTIFIC PROTOCOL

## 1. Research Questions
1. Does the presence of memoriX persistent memory significantly improve the task success rate of OpenCode agents compared to a stateless baseline?
2. At what cost (latency, tokens, computational overhead) does this improvement come?
3. How effectively does the system curate and retrieve relevant memories without human intervention (blind curation)?

## 2. Hypotheses
- **Primary Hypothesis (H1):** Agents equipped with `memorix_core` will complete complex, multi-turn, multi-session SDLC tasks at a statistically significant higher rate than the `no_memory` baseline.
- **Secondary Hypothesis (H2):** The overhead introduced by memory retrieval scales sub-linearly relative to the size of the Titan hot-site, maintaining acceptable bounds up to 5,000 active memories.

## 3. Variables
### Independent Variables
- **Memory Condition:** `no_memory` vs. `memorix_core` (and optionally `memorix_full`).
- **Memory Capacity:** Ranging from 10 to 100,000 memories depending on the volume profile.

### Dependent Variables (Metrics)
- **Task Success:** Binary (1 = success, 0 = failure).
- **Retrieval Quality:** Recall@K, MRR, Contamination Rate.
- **Cost Metrics:** Peak RSS, Execution Duration, Token Count, Tool Call Count.

## 4. Randomization & Balancing
- **Seeds:** All cases will be executed across a minimum of 5 distinct seeds.
- **Order Balancing (AB/BA):** To mitigate temporal API variations, the order of execution between `no_memory` (A) and `memorix` (B) must alternate strictly by seed (e.g., Seed 1: A then B; Seed 2: B then A).
- **Distractors:** For robustness tests, distractors will be randomized in insertion order to test for positional bias in retrieval.

## 5. Controls and Ablations
- **No-relevant-memory Control:** Tasks where memory is enabled, but the stored memories are entirely irrelevant to the task, measuring the cost and distraction penalty of the system.
- **Baseline Invariant Enforcement:** Any baseline (`no_memory`) run that attempts to load the MCP server, accesses Titan, or calls `memory_*` tools must be automatically excluded and marked as a systemic failure.

## 6. Exclusion Criteria
- **Predefined Technical Errors:** API timeouts, HTTP 401s, out-of-memory errors on the host OS. These trigger an automated retry.
- **Scientific Results (DO NOT RETRY):** Empty retrieval, LLM hallucinations, failure to follow instructions, bash recovery errors. These are valid failures and must be logged as such.

## 7. Statistical Tests
- **Significance Testing:** McNemar's test for paired binary outcomes (Task Success).
- **Effect Size:** Odds ratio for task completion.
- **Confidence Intervals:** 95% Confidence Intervals for continuous metrics (Latency, Tokens).
- **Power Analysis:** The sample sizes (detailed in the Sample Size Plan) target a statistical power of 0.80 at an alpha of 0.05.

## 8. Pre-registration
All protocols, exact commits, model versions, and expected dataset sizes must be logged and cryptographically hashed before the execution phase begins. No protocol modifications are permitted after observing preliminary results.
