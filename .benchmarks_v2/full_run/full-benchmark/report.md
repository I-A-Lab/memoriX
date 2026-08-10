# memoriX Benchmark Report

**Campaign ID:** `full-benchmark`

**Profile:** standard

**Families:** f01_exact_key_recall, f02_semantic_retrieval, f03_distractor_robustness, f04_multi_hop_reasoning, f05_temporal_decay, f06_contextual_disambiguation, f07_adversarial_injection, f08_cross_session_leak, f09_privacy_isolation, f10_consolidation_quality, f11_forgetting_curve, f12_capacity_management, f13_search_precision, f14_search_recall, f15_ranking_relevance, f16_query_expansion, f17_partial_match, f18_noise_tolerance, f19_schema_evolution, f20_version_awareness, f21_concurrent_access, f22_migration_safety, f23_api_conformance, f24_sdk_compatibility, f25_performance_baseline, f26_latency_budget, f27_memory_footprint, f28_streaming_integrity, f29_end_to_end_smoke, f30_reproducibility, f31_determinism_check, f32_golden_output


## 1. Executive Summary

- Total runs: 128
- Passed: 72
- Failed: 56
- Overall pass rate: 56.2%

## 2. Per-Family Metrics

| Family | Suite | Precision | Recall | F1 | Pass Rate | Median Lat. | P95 Lat. |
|--------|-------|-----------|--------|----|-----------|------------:|---------:|
| f01_exact_key_recall | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3098.4ms | 3245.4ms |
| f02_semantic_retrieval | standard | 0.5000 | 0.5000 | 0.5000 | 0.0% | 3467.8ms | 3473.7ms |
| f03_distractor_robustness | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3487.1ms | 3723.0ms |
| f04_multi_hop_reasoning | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 2873.4ms | 2945.0ms |
| f05_temporal_decay | standard | 0.3750 | 0.3750 | 0.3750 | 25.0% | 3033.3ms | 3080.6ms |
| f06_contextual_disambiguation | standard | 0.5500 | 0.5500 | 0.5500 | 25.0% | 3110.6ms | 3652.7ms |
| f07_adversarial_injection | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3140.4ms | 3461.3ms |
| f08_cross_session_leak | standard | 0.0000 | 0.0000 | 0.0000 | 0.0% | 3186.5ms | 3276.4ms |
| f09_privacy_isolation | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3115.3ms | 3115.5ms |
| f10_consolidation_quality | standard | 0.5000 | 0.5000 | 0.5000 | 0.0% | 3466.7ms | 3515.1ms |
| f11_forgetting_curve | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3667.9ms | 3691.2ms |
| f12_capacity_management | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 2983.8ms | 3122.7ms |
| f13_search_precision | standard | 0.3750 | 0.3750 | 0.3750 | 25.0% | 3012.3ms | 3046.9ms |
| f14_search_recall | standard | 0.5500 | 0.5500 | 0.5500 | 25.0% | 3162.7ms | 3643.8ms |
| f15_ranking_relevance | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3162.8ms | 3163.1ms |
| f16_query_expansion | standard | 0.0000 | 0.0000 | 0.0000 | 0.0% | 3186.0ms | 3393.8ms |
| f17_partial_match | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3071.3ms | 3075.6ms |
| f18_noise_tolerance | standard | 0.5000 | 0.5000 | 0.5000 | 0.0% | 3496.4ms | 3512.7ms |
| f19_schema_evolution | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3645.8ms | 3676.7ms |
| f20_version_awareness | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 2905.7ms | 2908.7ms |
| f21_concurrent_access | standard | 0.3750 | 0.3750 | 0.3750 | 25.0% | 3050.3ms | 3106.7ms |
| f22_migration_safety | standard | 0.5500 | 0.5500 | 0.5500 | 25.0% | 3123.2ms | 3676.4ms |
| f23_api_conformance | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3108.1ms | 3145.5ms |
| f24_sdk_compatibility | standard | 0.0000 | 0.0000 | 0.0000 | 0.0% | 3162.2ms | 3168.8ms |
| f25_performance_baseline | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3091.9ms | 3164.5ms |
| f26_latency_budget | standard | 0.5000 | 0.5000 | 0.5000 | 0.0% | 3514.0ms | 3796.9ms |
| f27_memory_footprint | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3616.1ms | 3669.2ms |
| f28_streaming_integrity | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 2952.9ms | 2971.5ms |
| f29_end_to_end_smoke | standard | 0.3750 | 0.3750 | 0.3750 | 25.0% | 3051.8ms | 3077.2ms |
| f30_reproducibility | standard | 0.5500 | 0.5500 | 0.5500 | 25.0% | 3229.6ms | 3658.9ms |
| f31_determinism_check | standard | 1.0000 | 1.0000 | 1.0000 | 100.0% | 3199.3ms | 3295.9ms |
| f32_golden_output | standard | 0.0000 | 0.0000 | 0.0000 | 0.0% | 3182.7ms | 3316.3ms |

## 3. f01_exact_key_recall - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3098.4ms
- P95 Latency: 3245.4ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 4. f02_semantic_retrieval - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5000
- Recall: 0.5000
- F1: 0.5000
- Median Latency: 3467.8ms
- P95 Latency: 3473.7ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 5. f03_distractor_robustness - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3487.1ms
- P95 Latency: 3723.0ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 6. f04_multi_hop_reasoning - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 2873.4ms
- P95 Latency: 2945.0ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 7. f05_temporal_decay - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.3750
- Recall: 0.3750
- F1: 0.3750
- Median Latency: 3033.3ms
- P95 Latency: 3080.6ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 8. f06_contextual_disambiguation - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5500
- Recall: 0.5500
- F1: 0.5500
- Median Latency: 3110.6ms
- P95 Latency: 3652.7ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 9. f07_adversarial_injection - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3140.4ms
- P95 Latency: 3461.3ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 10. f08_cross_session_leak - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.0000
- Recall: 0.0000
- F1: 0.0000
- Median Latency: 3186.5ms
- P95 Latency: 3276.4ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 11. f09_privacy_isolation - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3115.3ms
- P95 Latency: 3115.5ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 12. f10_consolidation_quality - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5000
- Recall: 0.5000
- F1: 0.5000
- Median Latency: 3466.7ms
- P95 Latency: 3515.1ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 13. f11_forgetting_curve - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3667.9ms
- P95 Latency: 3691.2ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 14. f12_capacity_management - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 2983.8ms
- P95 Latency: 3122.7ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 15. f13_search_precision - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.3750
- Recall: 0.3750
- F1: 0.3750
- Median Latency: 3012.3ms
- P95 Latency: 3046.9ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 16. f14_search_recall - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5500
- Recall: 0.5500
- F1: 0.5500
- Median Latency: 3162.7ms
- P95 Latency: 3643.8ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 17. f15_ranking_relevance - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3162.8ms
- P95 Latency: 3163.1ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 18. f16_query_expansion - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.0000
- Recall: 0.0000
- F1: 0.0000
- Median Latency: 3186.0ms
- P95 Latency: 3393.8ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 19. f17_partial_match - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3071.3ms
- P95 Latency: 3075.6ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 20. f18_noise_tolerance - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5000
- Recall: 0.5000
- F1: 0.5000
- Median Latency: 3496.4ms
- P95 Latency: 3512.7ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 21. f19_schema_evolution - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3645.8ms
- P95 Latency: 3676.7ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 22. f20_version_awareness - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 2905.7ms
- P95 Latency: 2908.7ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 23. f21_concurrent_access - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.3750
- Recall: 0.3750
- F1: 0.3750
- Median Latency: 3050.3ms
- P95 Latency: 3106.7ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 24. f22_migration_safety - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5500
- Recall: 0.5500
- F1: 0.5500
- Median Latency: 3123.2ms
- P95 Latency: 3676.4ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 25. f23_api_conformance - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3108.1ms
- P95 Latency: 3145.5ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 26. f24_sdk_compatibility - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.0000
- Recall: 0.0000
- F1: 0.0000
- Median Latency: 3162.2ms
- P95 Latency: 3168.8ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 27. f25_performance_baseline - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3091.9ms
- P95 Latency: 3164.5ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 28. f26_latency_budget - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5000
- Recall: 0.5000
- F1: 0.5000
- Median Latency: 3514.0ms
- P95 Latency: 3796.9ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 29. f27_memory_footprint - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3616.1ms
- P95 Latency: 3669.2ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 30. f28_streaming_integrity - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 2952.9ms
- P95 Latency: 2971.5ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 31. f29_end_to_end_smoke - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.3750
- Recall: 0.3750
- F1: 0.3750
- Median Latency: 3051.8ms
- P95 Latency: 3077.2ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 32. f30_reproducibility - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.5500
- Recall: 0.5500
- F1: 0.5500
- Median Latency: 3229.6ms
- P95 Latency: 3658.9ms
- Pass Rate: 25.0%
- Total Runs: 4
- Failed Runs: 3

## 33. f31_determinism_check - Detailed Results

### Metrics
- Suite: standard
- Precision: 1.0000
- Recall: 1.0000
- F1: 1.0000
- Median Latency: 3199.3ms
- P95 Latency: 3295.9ms
- Pass Rate: 100.0%
- Total Runs: 4
- Failed Runs: 0

## 34. f32_golden_output - Detailed Results

### Metrics
- Suite: standard
- Precision: 0.0000
- Recall: 0.0000
- F1: 0.0000
- Median Latency: 3182.7ms
- P95 Latency: 3316.3ms
- Pass Rate: 0.0%
- Total Runs: 4
- Failed Runs: 4

## 35. Failure Breakdown

Raw results not available for failure breakdown.

## 36. Configuration

- Profile: standard
- Families: f01_exact_key_recall, f02_semantic_retrieval, f03_distractor_robustness, f04_multi_hop_reasoning, f05_temporal_decay, f06_contextual_disambiguation, f07_adversarial_injection, f08_cross_session_leak, f09_privacy_isolation, f10_consolidation_quality, f11_forgetting_curve, f12_capacity_management, f13_search_precision, f14_search_recall, f15_ranking_relevance, f16_query_expansion, f17_partial_match, f18_noise_tolerance, f19_schema_evolution, f20_version_awareness, f21_concurrent_access, f22_migration_safety, f23_api_conformance, f24_sdk_compatibility, f25_performance_baseline, f26_latency_budget, f27_memory_footprint, f28_streaming_integrity, f29_end_to_end_smoke, f30_reproducibility, f31_determinism_check, f32_golden_output
- Campaign: full-benchmark
