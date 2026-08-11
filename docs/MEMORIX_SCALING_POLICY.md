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

## Elastic capacity contract

The hot site expands (never evicts) when validated memories would exceed the
baseline. All constants are the enforced defaults from
`ElasticCapacityPolicy`:

| Constant | Default | Meaning |
| --- | --- | --- |
| `minimum_growth` | 10 | minimum slot growth per expansion |
| `growth_factor` | 1.25 | multiplicative growth per expansion |
| `baseline_headroom_ratio` | 0.80 | occupancy threshold for restoration |
| `max_automatic_deactivations` | 200 | cap per nightly soft-prune |

Expanded capacity is computed as:

```text
new = max(current + minimum_growth, ceil(current * growth_factor),
          active_count + required_slots)
```

Examples: baseline 50 -> 63 (max(60, ceil(62.5), 51)); baseline 50,000 ->
62,500 (max(50,010, 62,500, active + required)). Expansion is active whenever
`current_capacity > baseline_capacity`.

## Baseline restoration

The nightly restores the baseline only when the active population fits with
headroom AND the consistency gate passes:

```text
active_after <= floor(baseline_capacity * 0.80)
```

Examples: baseline 50 with floor(50 * 0.8) == 40 restores at 40 active and
stays expanded at 51 active; baseline 50,000 restores at 40,000 active.
Automatic soft-forgets are applied by the fixed reviewer constant
`NIGHTLY_CAPACITY_REVIEWER == "memorix_nightly_capacity"` with the run
reference in the forget reason, capped by `max_automatic_deactivations`.

## Nightly pressure observation

The nightly observes pressure with the usage-only weight override:

```text
PressureWeights(usage_ratio=1.0, momentum=0.0, entropy=0.0,
                surprise=0.0, persistence=0.0)
```

so `memory_pressure == active / current_capacity`. The default
`SoftPruningPolicy.minimum_pressure` (0.70) is therefore reachable at >= 70%
usage and the automatic soft-pruning branch is never a dead canary.

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
- change the configured Hot/STM/Cold retrieval hierarchy or rehydrate Cold data into Titan;
- apply pruning from OpenCode hooks;
- mutate the runtime during synthetic benchmarks.
