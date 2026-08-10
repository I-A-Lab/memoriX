# MEMORIX BENCHMARK REPORT SPECIFICATION

The final benchmark reporting engine must automatically compile results into Markdown, DOCX, PDF, and machine-readable JSON formats. The report must contain the following 30 structured sections.

## Report Structure
1. **Executive summary:** High-level win/tie/loss metrics and core conclusion.
2. **Project architecture:** Brief summary of the memoriX MCP flow.
3. **Research questions:** The primary objectives of the campaign.
4. **Hypotheses:** Defined hypotheses tested by the data.
5. **Experimental design:** Explanation of AB/BA balancing, seeds, and invariant controls.
6. **Hardware/software environment:** Exact Git commits, OS, RAM, CPU, and Python versions.
7. **Datasets:** Manifest of tasks and domains used.
8. **Internal OpenCode A/B:** Results of the internal cross-session SDLC campaigns.
9. **Galileo-derived:** Community proxy metrics.
10. **BFCL-derived:** Function calling and retrieval accuracy metrics.
11. **Arena-inspired:** Extrapolations based on Agent Arena task methodologies.
12. **Multi-agent:** Shared Titan manager/worker task success rates.
13. **Memory-pure:** Latency and retrieval accuracy independent of LLM context window limits.
14. **Retrieval:** Recall@1, Recall@5, MRR, and distractor intrusion rates.
15. **Capacity and expansion:** Validation of scale from 10 to 100,000 memories and manual vs automatic expansion behavior.
16. **Nightly and consolidation:** Cost and success rate of batch background operations.
17. **Supersession and contradictions:** Handling of factual updates and contradictory state.
18. **Isolation:** Cross-tenant and cross-project contamination tests.
19. **Ablations:** Impact of removing consolidation, active routing, or topic blocks.
20. **Performance and resources:** Peak RSS, disk footprint, token overhead, and wall-clock time.
21. **Statistical analysis:** McNemar's test results, p-values, and confidence intervals.
22. **Failure taxonomy:** Breakdown of errors by `TECH_`, `AGENT_`, and `MEM_` categories.
23. **Exclusions:** Log of all technical retries and aborted runs.
24. **Threats to validity:** Internal and external biases (e.g., overfitting to internal tasks).
25. **Supported conclusions:** Defensible claims backed by statistical significance.
26. **Unsupported conclusions:** Claims the data specifically does *not* support (e.g., official leaderboard scores).
27. **Future work:** Prioritized engineering tasks based on failure bottlenecks.
28. **Reproduction guide:** Exact commands required to rerun the campaign locally.
29. **Appendices:** Additional raw data slices and verbose error logs.
30. **Sources, hashes and manifests:** Cryptographic hashes of all datasets, runtimes, and baseline code states.

## Formatting Requirements
- All comparative metrics must show baseline vs. memoriX side-by-side.
- Visualizations required:
  - Bar charts for win/tie/loss.
  - Boxplots for execution duration and tool calls (showing median, p50, p90, p95, p99).
  - Line graphs for retrieval latency vs. memory volume.
- No percentages from different protocols may be merged or averaged together.
