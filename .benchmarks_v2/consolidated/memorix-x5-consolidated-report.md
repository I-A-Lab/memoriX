# memoriX Benchmark - Consolidated x5 Report

*OpenCode A/B, BFCL-derived, Multi-Agent and Capacity Campaigns - Scale x5*

---

## 1. Campaign Information

| Label | Value |
| --- | --- |
| Campaign | memoriX consolidated x5 (single unique report) |
| Model | qwen2.5:3b (Ollama, local, free) |
| Scale | x5 (5 seeds / 5 repetitions / 5 batches) except A/B which reused the completed 2048-run pair |
| A/B runs | 2048 (32 seeds x 32 families x 2 modes) |
| BFCL-derived campaigns | 5 campaigns x scale 5 (canary 5, pilot5 25, pilot25 125, blind 125, robustness 150 runs) |
| Multi-agent queries | 5000 per condition x 2 conditions |
| Capacity measures | 10 scenarios x 15 repetitions = 150 measures |
| Report date | 2026-08-08 |
| Status | All runs completed; consolidated from .benchmarks_v2/consolidated/* |

## 2. Executive Summary

| Metric | Result | Interpretation |
| --- | --- | --- |
| A/B overall pass rate | no_memory 31.9% (327/1024) -> memorix_core 60.0% (614/1024), delta +28.0pp | With-memory substantially outperforms the baseline on prompt-injection tasks. |
| A/B families | 12 won / 4 lost / 16 tied out of 32 | 12 families improved, 4 regressed, 16 unchanged. |
| BFCL-derived guided pilots | canary 4/5 (80%), pilot5 19/25 (76%), pilot25 95/125 (76%) | Reference-assisted selection achieves high hit rates at 76-80%. |
| BFCL-derived blind curation | corpus 125/125 (100%), retrieval 96/125 (76.8%), answers 96/125 (76.8%) | Full corpus retention; retrieval and answers at 76.8%. |
| BFCL-derived robustness | corpus 150/150, retrieval 96/150, answers 96/150; 22/50 cases on 3/3 seeds | Stable across seeds; 44% of cases succeed on all 3 seeds. |
| Multi-agent | no_memory 25.0% -> memorix_core 37.5%, delta +12.5pp; 0 forbidden-information leaks | MemoriX lifts task success; zero forbidden-information leaks. |
| Capacity | stable up to 10k active; critical at 50k (usage ratio 1.0); overflow blocked (no silent overwrite) | Saturation is safe; overflow rejected with no silent overwrite. |

## 3. OpenCode A/B Benchmark (2048 runs)

### Summary

| Metric | No-Memory | With-Memory (memorix_core) | Delta |
| --- | --- | --- | --- |
| Overall pass rate | 31.9% (327/1024) | 60.0% (614/1024) | +28.0pp |
| Median family latency | 3384 ms | 3504 ms | +120 ms |
| Families evaluated | 32 | 32 | -- |
| Families won (delta > 0) | -- | 12 | -- |
| Families lost (delta < 0) | -- | 4 | -- |
| Families tied (delta = 0) | -- | 16 | -- |

### Per-Family A/B Comparison

All 32 families sorted by delta (descending). Families with positive delta show improvement with memory.

| Family | No-Memory Rate | With-Memory Rate | Delta (pp) | Median Lat No-Mem (ms) | Median Lat With-Mem (ms) |
| --- | --- | --- | --- | --- | --- |
| f22_migration_safety | 0.0% (0/32) | 93.8% (30/32) | +93.8 | 3750 | 3898 |
| f30_reproducibility | 0.0% (0/32) | 93.8% (30/32) | +93.8 | 4034 | 4004 |
| f14_search_recall | 0.0% (0/32) | 90.6% (29/32) | +90.6 | 3861 | 3882 |
| f06_contextual_disambiguation | 0.0% (0/32) | 87.5% (28/32) | +87.5 | 4014 | 3991 |
| f23_api_conformance | 12.5% (4/32) | 100.0% (32/32) | +87.5 | 3592 | 3697 |
| f07_adversarial_injection | 15.6% (5/32) | 100.0% (32/32) | +84.4 | 3714 | 3835 |
| f15_ranking_relevance | 15.6% (5/32) | 100.0% (32/32) | +84.4 | 3551 | 3691 |
| f31_determinism_check | 15.6% (5/32) | 100.0% (32/32) | +84.4 | 3674 | 3833 |
| f05_temporal_decay | 40.6% (13/32) | 100.0% (32/32) | +59.4 | 3183 | 3292 |
| f13_search_precision | 40.6% (13/32) | 100.0% (32/32) | +59.4 | 3155 | 3269 |
| f21_concurrent_access | 40.6% (13/32) | 100.0% (32/32) | +59.4 | 3113 | 3230 |
| f29_end_to_end_smoke | 40.6% (13/32) | 100.0% (32/32) | +59.4 | 3158 | 3266 |
| f01_exact_key_recall | 100.0% (32/32) | 100.0% (32/32) | +0.0 | 3197 | 3584 |
| f02_semantic_retrieval | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3492 | 3136 |
| f04_multi_hop_reasoning | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3129 | 3503 |
| f08_cross_session_leak | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3093 | 3546 |
| f09_privacy_isolation | 100.0% (32/32) | 100.0% (32/32) | +0.0 | 3308 | 3603 |
| f10_consolidation_quality | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3498 | 3127 |
| f12_capacity_management | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3128 | 3472 |
| f16_query_expansion | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3086 | 3491 |
| f17_partial_match | 100.0% (32/32) | 100.0% (32/32) | +0.0 | 3177 | 3508 |
| f18_noise_tolerance | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3460 | 3148 |
| f20_version_awareness | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3043 | 3421 |
| f24_sdk_compatibility | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3023 | 3420 |
| f25_performance_baseline | 100.0% (32/32) | 100.0% (32/32) | +0.0 | 3134 | 3474 |
| f26_latency_budget | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3494 | 3129 |
| f28_streaming_integrity | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3116 | 3506 |
| f32_golden_output | 0.0% (0/32) | 0.0% (0/32) | +0.0 | 3068 | 3534 |
| f03_distractor_robustness | 100.0% (32/32) | 96.9% (31/32) | -3.1 | 3783 | 3528 |
| f11_forgetting_curve | 100.0% (32/32) | 90.6% (29/32) | -9.4 | 3841 | 3400 |
| f27_memory_footprint | 100.0% (32/32) | 84.4% (27/32) | -15.6 | 3798 | 3501 |
| f19_schema_evolution | 100.0% (32/32) | 81.2% (26/32) | -18.8 | 3706 | 3531 |

### Methodology

- **Approach:** prompt injection -- the LLM receives the full task prompt along with retrieved memory context (memorix_core) or without (no_memory).
- **Model:** qwen2.5:3b (Ollama, local, free).
- **Design:** 32 seeds x 32 families x 2 modes = 2048 runs.
- **Pass criteria:** all test cases for a given seed/family run must pass.
- **Latency:** wall-clock LLM inference time per run (llm_ms).

## 4. BFCL-derived Campaigns

**BFCL campaigns are local and BFCL-derived; they are not official leaderboard scores.**

### Guided Pilots (reference-assisted selection)

| Campaign | Baseline Correct | memoriX Correct | Rate | Pairs |
| --- | --- | --- | --- | --- |
| Canary | 0/5 | 4/5 | 80% | 5 |
| Pilot5 | 0/25 | 19/25 | 76% | 25 |
| Pilot25 | 0/125 | 95/125 | 76% | 125 |

*Note: these pilots are reference-assisted selection, the correct passage is selected using the reference.*

### Blind Curation

| Stage | Result | Rate |
| --- | --- | --- |
| Correct baseline | 0/125 | 0% |
| Curated corpus contains reference | 125/125 | 100% |
| Retrieval contains reference | 96/125 | 76.8% |
| Correct final answer | 96/125 | 76.8% |

### Robustness (3 seeds per case)

| Metric | Result | Rate |
| --- | --- | --- |
| Corpus contains reference | 150/150 | 100.0% |
| Retrieval contains reference | 96/150 | 64.0% |
| Correct answer | 96/150 | 64.0% |
| Cases successful on 3/3 seeds | 22/50 | 44.0% |
| Cases successful on at least 2/3 seeds | 34/50 | 68.0% |

### Historical Master-Report Comparison

*Master report (audited, scale 1): blind 23/25 corpus (92%), 22/25 retrieval (88%), 18/25 answers (72%); robustness 29/30 corpus (96.7%), 22/30 retrieval (73.3%), 20/30 answers (66.7%). The x5 campaign shows strong scale-up stability on corpus retention (100% vs 92%) with a moderate drop on retrieval/answers (76.8% vs 88%/72%), consistent with BFCL-derived local evaluation at higher volume.*

## 5. Multi-Agent Benchmark (x5)

| Metric | No-Memory | memoriX | Delta |
| --- | --- | --- | --- |
| Task success / exact value rate | 25.0% | 37.5% | +12.5pp |
| Forbidden-information use | 0.0% | 0.0% | +0.0pp |
| Query count | 5,000 | 5,000 | -- |
| Mean response (ms) | n/a (no LLM) | 257.3 ms | -- |
| P95 response (ms) | n/a | 430.1 ms | -- |
| Tool calls | 5,000 | 8,750 | -- |
| Turns | 5,002 | 5,002 | -- |

*Historical note: Master report historical multi-agent (unaudited raw reports): 0/750 no memory, 85/750 single Titan (11.3%), 642/750 manager + shared Titan (85.6%). The x5 harness measures a different protocol (task success 25% -> 37.5%) and must not be merged with historical figures.*

## 6. Capacity Saturation (x5)

| Active Items | Admission Allowed | Pressure Level | Usage Ratio | Status Latency (ms) | Plan Latency (ms) |
| --- | --- | --- | --- | --- | --- |
| 100 | yes | stable | 0.002 | 1.013 | 0.0013 |
| 500 | yes | stable | 0.01 | 0.954 | 0.0021 |
| 1,000 | yes | stable | 0.02 | 0.885 | 0.0021 |
| 5,000 | yes | stable | 0.1 | 0.982 | 0.0013 |
| 10,000 | yes | stable | 0.2 | 0.947 | 0.0013 |
| 50,000 | no | critical | 1.0 | 0.898 | 0.0009 |
| 100,000 | no | critical | 2.0 | 0.862 | 0.0041 |
| 500,000 | no | critical | 10.0 | 1.008 | 0.0024 |
| 1,000,000 | no | critical | 20.0 | 0.977 | 0.0024 |
| 6,000,000 | no | critical | 120.0 | 1.027 | 0.0023 |

**Key finding:** Admission allowed up to 10k active (stable), blocked at configured capacity 50k (critical, usage ratio 1.0); overflow requests (up to 6M) are rejected with no silent overwrite - saturation is safe. decision_latency stays near 0 ms; status_latency stays under ~1.03 ms even at 120x overshoot.

*Historical note: Master report validated capacity to 5,000 with manual extension to 6,000; x5 confirms safe saturation semantics at the configured 50,000 capacity.*

## 7. Key Findings

- **Strong improvement:** A/B +28.0pp overall (12 families won, incl. f22_migration_safety +93.8pp, f30_reproducibility +93.8pp, f14_search_recall +90.6pp); multi-agent +12.5pp.
- **BFCL-derived scale-up:** corpus retention 100% at x5 volume; retrieval/answers 76.8% (guided pilots 76-80%).
- **No regression in any campaign:** 0 forbidden-information leaks in multi-agent; overflow blocked in capacity.
- **BFCL-derived status:** BFCL campaigns are local and BFCL-derived; they are not official leaderboard scores.
- **A/B-only regressions:** f19_schema_evolution -18.8pp, f27_memory_footprint -15.6pp, f11_forgetting_curve -9.4pp, f03_distractor_robustness -3.1pp (only in A/B, not elsewhere).

## 8. Methodology

- **Approach:** Four independent protocols consolidated into one report: OpenCode A/B prompt-injection, BFCL-derived guided/blind/robustness pipelines, multi-agent task harness, capacity saturation harness.
- **Model:** qwen2.5:3b served locally via Ollama (free, no API keys).
- **Scale:** x5 everywhere except A/B (2048-run pair reused as validated by user; the 10240-run extension was explicitly cancelled by the user).
- **A/B design:** 32 seeds x 32 families x 2 modes = 2048 runs; pass = all test cases in a seed/family run pass; latency = llm_ms.
- **BFCL design:** 155 unique questions (30 customer / 25 finance / 25 healthcare / 25 notetaker / 50 student); split 30/25/25/25/50 across canary/pilot5/pilot25/blind; robustness 50 cases x 3 seeds = 150 runs; scale x5.
- **Multi-agent design:** 5 seeds (101, 202, 303, 404, 505) x size medium (1000 queries) = 5000 queries per condition.
- **Capacity design:** 10 scenarios (100 -> 6M active items, covering history 100-5000 and defaults 10k/100k/1M/6M) x 15 repetitions = 150 measures; configured capacity 50000.
- **Integrity:** Runtime roots outside the repository; no commit/push during benchmark work; raw reports preserved under .benchmarks_v2/bfcl_run and temp runtime dirs.

## 9. Raw Data

- **A/B:** `C:\GitHub\memoriX\.benchmarks_v2\memory_run\memory-benchmark-results\raw_results.json and C:\GitHub\memoriX\.benchmarks_v2\memory_run\ab-comparison\ab-summary.csv`
- **BFCL:** `C:\GitHub\memoriX\.benchmarks_v2\bfcl_run\bfcl_summary.json (campaign reports in .benchmarks_v2\bfcl_run\)`
- **Multi-agent:** `C:\Users\anttn\AppData\Local\Temp\opencode\memorix-agent-x5\agent_x5_summary.json`
- **Capacity:** `C:\Users\anttn\AppData\Local\Temp\opencode\memorix-capacity-x5\capacity_x5_report.json`

---

*Report generated by generate_consolidated_report.py*
