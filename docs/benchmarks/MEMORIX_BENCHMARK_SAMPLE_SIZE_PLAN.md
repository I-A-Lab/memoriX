# MEMORIX BENCHMARK SAMPLE SIZE PLAN

To achieve statistical significance and provide undeniable evidence of memoriX's impact, the benchmark campaign is divided into progressive volume profiles.

## 1. Smoke Profile
- **Goal:** Technical verification of the benchmark harness and MCP transport.
- **Tasks:** 5 pairs.
- **Seeds:** 1.
- **Memory Volume:** Tiny (10 memories, 20 distractors).
- **Cost/Time:** Negligible / < 10 minutes.

## 2. Pilot Profile
- **Goal:** Variance estimation and cost forecasting.
- **Tasks:** 25 pairs.
- **Seeds:** 3.
- **Memory Volume:** Small (100 memories, 100 distractors).
- **Cost/Time:** Low API cost / ~1 hour.
- **Conditions for advancement:** 100% technical stability, expected failure taxonomy observed.

## 3. Standard Profile
- **Goal:** Reasonable research baseline for intermediate reporting.
- **Tasks:** 150 pairs.
- **Seeds:** 5.
- **Memory Volume:** Medium (1,000 memories, 2,000 distractors).
- **Cost/Time:** Moderate API cost / ~12 hours.

## 4. Large Profile
- **Goal:** Robust scientific evaluation targeting statistical significance across all sub-domains.
- **Tasks:** 500 pairs.
- **Seeds:** 5.
- **Memory Volume:** Large (10,000 memories, 20,000 distractors).
- **Cost/Time:** High API cost / ~2-3 days.

## 5. Research / Extreme Profile
- **Goal:** The definitive final campaign for publication and long-term validity.
- **Tasks:** 1,000+ pairs.
- **Seeds:** 5.
- **Memory Volume:** Stress (50,000 memories) & Extreme (100,000 memories, 250,000 distractors).
- **Special Conditions:** Requires explicit manual execution due to massive API cost and temporal length. Will include 750+ multi-agent shared Titan runs.
- **Cost/Time:** Very High API cost / > 1 week.

## Stop Conditions
The execution of a profile must be immediately aborted if:
1. The `no_memory` invariant is violated (e.g., tools exposed to baseline).
2. Systematic API provider failure (>10% HTTP 401/500 errors).
3. The cryptographic verification of the environment hash fails.
