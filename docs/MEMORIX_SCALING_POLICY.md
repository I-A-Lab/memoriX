# memoriX Scaling Policy

## Storage roles

The hot site is bounded active memory optimized for retrieval. The cold site is
durable append-only history. Capacity management applies only to the hot site.

## Default limits and pressure

The default configured Titan capacity is 50,000 active memories. Runtime status
uses deterministic pressure levels:

| Active usage | Level |
| --- | --- |
| below 80% | stable |
| 80% to below 90% | watch |
| 90% to below 100% | high |
| 100% or above | critical |

The configured value remains overridable. Admission is allowed only while the
active count is strictly below capacity.

## Saturation behavior

At capacity, memoriX does not silently overwrite memory. Candidate validation
is rejected before mutation and the candidate stays pending. The operator may
review a dry-run soft-pruning plan and explicitly authorize deactivation.

## Six-million-item requirement

The six-million scenario is a calculation and protocol validation target, not
a requirement to materialize six million Python objects or Titan records on a
developer workstation. The benchmark uses bounded samples of at most 256 plan
items while preserving the true active-count arithmetic.

## Non-goals

Capacity management does not:

- hard-delete hot memories;
- delete or compact the cold archive;
- automatically rehydrate cold history;
- create a cold-search fallback for normal retrieval;
- apply pruning from OpenCode hooks;
- mutate the runtime during synthetic benchmarks.
