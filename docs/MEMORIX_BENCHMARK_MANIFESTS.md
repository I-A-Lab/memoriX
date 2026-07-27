# memoriX benchmark manifests

Part 31 introduces an immutable manifest written before every global benchmark run.

The manifest records the mode, suite, size, seed, task, dataset, prompt version,
model parameters, budgets, evaluator version, Git commit, dirty state, Python and
Bun versions, hardware fingerprint, runtime path and configuration fingerprint.

## Safety invariants

- `no_memory` never receives a memoriX runtime path.
- Memory-enabled modes require an isolated runtime outside the repository.
- Existing manifests are never overwritten.
- Configuration fingerprints are recalculated when manifests are loaded.
- Timestamps are UTC ISO-8601 values ending in `Z`.
- Failed and successful executions will later reference the same immutable manifest.

## Commands

Create a manifest from a request:

```powershell
py -3.10 .\scripts\memorix_benchmark_manifest.py capture `
    --request .\benchmarks\memorix_vs_no_memory\configs\default_run.json `
    --output "$env:TEMP\memorix-run-manifest.json"
```

Validate an existing manifest:

```powershell
py -3.10 .\scripts\memorix_benchmark_manifest.py validate `
    --manifest "$env:TEMP\memorix-run-manifest.json"
```

The default request is an example only. Published results must use versioned,
scenario-specific requests introduced by later benchmark parts.
