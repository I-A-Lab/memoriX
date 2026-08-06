# memoriX dynamic memory lifecycle benchmark

Part 41 evaluates the real public Python gateway and the real Titan hot site.
It does not use an LLM or a remote model provider.

The benchmark checks:

- creation and exact retrieval;
- paraphrased retrieval;
- versioned replacement and old-memory deactivation;
- persistence after gateway restart;
- isolation of similar decisions from different projects;
- explicit soft-forget persistence;
- short-term event consolidation into a pending candidate;
- human validation of the consolidated candidate;
- retrieval after restart;
- duplicate consolidation prevention;
- durable cold-history search;
- protected source-file integrity.

All runtime files and result files are written outside the repository.

Profiles:

- `quick`: 2 seeds, 25 distractors, 2 updates;
- `standard`: 3 seeds, 250 distractors, 3 updates;
- `stress`: 3 seeds, 1,000 distractors, 5 updates.

Run `quick` first and inspect its ZIP before using a larger profile.
