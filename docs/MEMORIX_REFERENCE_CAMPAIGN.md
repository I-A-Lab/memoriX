# memoriX real reference campaign

Part 40.5 runs the real memoriX gateway instead of the lexical fallback.

The initial reference campaign uses:

- size `small`;
- seeds `101`, `202`, and `303`;
- pure-memory lexical control;
- pure-memory real memoriX;
- multi-session no-memory baseline;
- multi-session real memoriX.

Every dataset, runtime, raw report, JSONL result, aggregate, and manifest is preserved outside the repository. The command can also create a ZIP ready for external analysis.

This campaign validates the memory layer and the no-memory agent comparison. It does not yet constitute a full end-to-end OpenCode task benchmark.
