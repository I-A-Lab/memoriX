# A/B Comparison Report: memoriX Core vs No-Memory Baseline

---

## Executive Summary

| Metric | No-Memory | With-Memory (memorix_core) | Delta |
|--------|-----------|---------------------------|-------|
| Overall pass rate | 31.9% (327/1024) | 60.0% (614/1024) | **+28.0pp** |
| Median family latency | 3384 ms | 3504 ms | +120 ms |
| Families evaluated | 32 | 32 | — |
| Families won (delta > 0) | — | 12 | — |
| Families lost (delta < 0) | — | 4 | — |
| Families tied (delta = 0) | — | 16 | — |

## Per-Family A/B Comparison

| Family | No-Memory Rate | With-Memory Rate | Delta (pp) | Median Lat No-Mem (ms) | Median Lat With-Mem (ms) |
|--------|---------------|------------------|------------|------------------------|--------------------------|
| `f22_migration_safety` | 0.0% (0/32) | 93.8% (30/32) | **+93.8** | 3750 | 3898 |
| `f30_reproducibility` | 0.0% (0/32) | 93.8% (30/32) | **+93.8** | 4034 | 4004 |
| `f14_search_recall` | 0.0% (0/32) | 90.6% (29/32) | **+90.6** | 3861 | 3882 |
| `f06_contextual_disambiguation` | 0.0% (0/32) | 87.5% (28/32) | **+87.5** | 4014 | 3991 |
| `f23_api_conformance` | 12.5% (4/32) | 100.0% (32/32) | **+87.5** | 3592 | 3697 |
| `f07_adversarial_injection` | 15.6% (5/32) | 100.0% (32/32) | **+84.4** | 3714 | 3835 |
| `f15_ranking_relevance` | 15.6% (5/32) | 100.0% (32/32) | **+84.4** | 3551 | 3691 |
| `f31_determinism_check` | 15.6% (5/32) | 100.0% (32/32) | **+84.4** | 3674 | 3833 |
| `f05_temporal_decay` | 40.6% (13/32) | 100.0% (32/32) | **+59.4** | 3183 | 3292 |
| `f13_search_precision` | 40.6% (13/32) | 100.0% (32/32) | **+59.4** | 3155 | 3269 |
| `f21_concurrent_access` | 40.6% (13/32) | 100.0% (32/32) | **+59.4** | 3113 | 3230 |
| `f29_end_to_end_smoke` | 40.6% (13/32) | 100.0% (32/32) | **+59.4** | 3158 | 3266 |
| `f01_exact_key_recall` | 100.0% (32/32) | 100.0% (32/32) | **+0.0** | 3197 | 3584 |
| `f02_semantic_retrieval` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3492 | 3136 |
| `f04_multi_hop_reasoning` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3129 | 3503 |
| `f08_cross_session_leak` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3093 | 3546 |
| `f09_privacy_isolation` | 100.0% (32/32) | 100.0% (32/32) | **+0.0** | 3308 | 3603 |
| `f10_consolidation_quality` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3498 | 3127 |
| `f12_capacity_management` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3128 | 3472 |
| `f16_query_expansion` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3086 | 3491 |
| `f17_partial_match` | 100.0% (32/32) | 100.0% (32/32) | **+0.0** | 3177 | 3508 |
| `f18_noise_tolerance` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3460 | 3148 |
| `f20_version_awareness` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3043 | 3421 |
| `f24_sdk_compatibility` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3023 | 3420 |
| `f25_performance_baseline` | 100.0% (32/32) | 100.0% (32/32) | **+0.0** | 3134 | 3474 |
| `f26_latency_budget` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3494 | 3129 |
| `f28_streaming_integrity` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3116 | 3506 |
| `f32_golden_output` | 0.0% (0/32) | 0.0% (0/32) | **+0.0** | 3068 | 3534 |
| `f03_distractor_robustness` | 100.0% (32/32) | 96.9% (31/32) | **-3.1** | 3783 | 3528 |
| `f11_forgetting_curve` | 100.0% (32/32) | 90.6% (29/32) | **-9.4** | 3841 | 3400 |
| `f27_memory_footprint` | 100.0% (32/32) | 84.4% (27/32) | **-15.6** | 3798 | 3501 |
| `f19_schema_evolution` | 100.0% (32/32) | 81.2% (26/32) | **-18.8** | 3706 | 3531 |

## Key Findings

### Strong Improvement (>= +25pp)

- **`f22_migration_safety`**: +93.8pp (0% -> 94%)
- **`f30_reproducibility`**: +93.8pp (0% -> 94%)
- **`f14_search_recall`**: +90.6pp (0% -> 91%)
- **`f06_contextual_disambiguation`**: +87.5pp (0% -> 88%)
- **`f23_api_conformance`**: +87.5pp (12% -> 100%)
- **`f07_adversarial_injection`**: +84.4pp (16% -> 100%)
- **`f15_ranking_relevance`**: +84.4pp (16% -> 100%)
- **`f31_determinism_check`**: +84.4pp (16% -> 100%)
- **`f05_temporal_decay`**: +59.4pp (41% -> 100%)
- **`f13_search_precision`**: +59.4pp (41% -> 100%)
- **`f21_concurrent_access`**: +59.4pp (41% -> 100%)
- **`f29_end_to_end_smoke`**: +59.4pp (41% -> 100%)

### Moderate Improvement (+5pp to +25pp)

- No families with moderate improvement.

### No Significant Improvement / Regression (< +5pp)

- **`f19_schema_evolution`**: -18.8pp (REGRESSION) (100% -> 81%)
- **`f27_memory_footprint`**: -15.6pp (REGRESSION) (100% -> 84%)
- **`f11_forgetting_curve`**: -9.4pp (REGRESSION) (100% -> 91%)
- **`f03_distractor_robustness`**: -3.1pp (REGRESSION) (100% -> 97%)
- **`f01_exact_key_recall`**: +0.0pp (no change) (100% -> 100%)
- **`f02_semantic_retrieval`**: +0.0pp (no change) (0% -> 0%)
- **`f04_multi_hop_reasoning`**: +0.0pp (no change) (0% -> 0%)
- **`f08_cross_session_leak`**: +0.0pp (no change) (0% -> 0%)
- **`f09_privacy_isolation`**: +0.0pp (no change) (100% -> 100%)
- **`f10_consolidation_quality`**: +0.0pp (no change) (0% -> 0%)
- **`f12_capacity_management`**: +0.0pp (no change) (0% -> 0%)
- **`f16_query_expansion`**: +0.0pp (no change) (0% -> 0%)
- **`f17_partial_match`**: +0.0pp (no change) (100% -> 100%)
- **`f18_noise_tolerance`**: +0.0pp (no change) (0% -> 0%)
- **`f20_version_awareness`**: +0.0pp (no change) (0% -> 0%)
- **`f24_sdk_compatibility`**: +0.0pp (no change) (0% -> 0%)
- **`f25_performance_baseline`**: +0.0pp (no change) (100% -> 100%)
- **`f26_latency_budget`**: +0.0pp (no change) (0% -> 0%)
- **`f28_streaming_integrity`**: +0.0pp (no change) (0% -> 0%)
- **`f32_golden_output`**: +0.0pp (no change) (0% -> 0%)

## Methodology

- **Approach**: Prompt injection -- the LLM receives the full task prompt along with retrieved memory context (memorix_core) or without (no_memory).
- **Model**: `qwen2.5:3b` served locally via Ollama.
- **Design**: 32 seeds x 32 families x 2 modes = 2048 total runs.
- **Pass criteria**: All test cases for a given seed/family must pass for the run to be marked passed.
- **Latency**: Wall-clock LLM inference time per run (llm_ms).

## Raw Data

Source file: `C:\GitHub\memoriX\.benchmarks_v2\memory_run\memory-benchmark-results\raw_results.json`
CSV summary: `C:\GitHub\memoriX\.benchmarks_v2\memory_run\ab-comparison\ab-summary.csv`

---
*Report generated by `generate_ab_report.py`*
