# memoriX benchmark datasets

Part 32 introduces deterministic and versioned benchmark datasets.

## Principles

- The same request and seed produce byte-identical JSONL files.
- Every dataset includes an integrity manifest with SHA-256 digests.
- Existing non-empty output directories are never overwritten.
- Generated datasets contain no real personal data or production secrets.
- Heavy profiles are generated only on explicit request.

## Families

The official families are user profiles, project facts, code decisions,
contradictions, updates, forgotten facts, duplicates, temporal facts and
distractors.

## Files

A generated dataset directory contains:

- `records.jsonl`: memories to store or archive;
- `queries.jsonl`: expected retrieval cases;
- `dataset_manifest.json`: counts, versions and integrity hashes.

## Reproduction

```powershell
py -3.10 .\scripts\memorix_generate_datasets.py generate `
    --request .\benchmarks\memorix_vs_no_memory\configs\default_dataset.json `
    --output <OUTSIDE_REPOSITORY_PATH>
```

Validation:

```powershell
py -3.10 .\scripts\memorix_generate_datasets.py validate `
    --dataset <DATASET_PATH>
```
