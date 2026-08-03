# memoriX adaptive retention scoring

Part 21 adds deterministic, explainable retention scoring for persisted hot-site memories.

The score combines importance, recency, usage, retrieval quality, confidence, momentum, and surprise. Inactive and replaced memories receive explicit penalties. Protected, pinned, or not-yet-human-validated memories are never recommended for deactivation.

The runtime reader consumes only the persisted Titan metadata JSONL file. It does not load Titan, access the cold site, write to the runtime, deactivate memories, or apply pruning.

The public dry-run operations are:

- `memorix_retention_ranking_status`
- `memorix_retention_ranking_inspect`
- `retention_ranking_status`
- `retention_ranking_inspect`

The CLI is:

```powershell
py -3.10 .\tools\memorix\diagnostics\memorix_retention_ranking.py --pretty
```

Bounded simulation is available through `--simulate-count`; it does not allocate the simulated population.
