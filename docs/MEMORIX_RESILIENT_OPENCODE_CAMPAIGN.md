# Resilient real OpenCode A/B campaign

Part 40.8 hardens the real OpenCode benchmark without modifying Titan,
the gateway, MCP, the hot site, or OpenCode.

It adds:

- automatic retries for provider, network, timeout, and early CLI failures;
- per-attempt logs;
- resumable output directories;
- checkpoint reuse for technically valid runs;
- valid-only quality aggregation;
- invalid-pair exclusion;
- counting of all memory/project tools, not only `memory_retrieve`;
- final source-integrity verification;
- no final ZIP until every A/B pair is technically valid.

The `large` profile runs 48 OpenCode executions across three seeds, eight
task families, two modes, and 1,000 distractor memories per seed.
