# memoriX Capacity Operations

## Purpose

Capacity controls protect the bounded Titan hot site while preserving the
append-only cold archive. Capacity inspection and planning are read-only.
Pruning is an explicit, permission-gated soft deactivation.

## Runtime files

Capacity operations live outside the repository under:

```text
<runtime>/operations/capacity/
|-- capacity.lock
|-- events.jsonl
`-- latest.json
```

`events.jsonl` is append-only operational history. `latest.json` is the most
recent event snapshot. `capacity.lock` prevents concurrent capacity mutations.

## Native operations

| Operation | Mutation | Permission |
| --- | --- | --- |
| `memory_capacity_status` | No | allow |
| `memory_capacity_plan` | No | allow |
| `memory_capacity_prune` | Yes, soft deactivation only | ask |

The MCP equivalents are `memorix_capacity_status`,
`memorix_capacity_plan`, and `memorix_capacity_prune`.

## Status and simulation

A synthetic status can model large populations without allocating them:

```powershell
py -3.10 ".\tools\memorix\diagnostics\memorix_capacity_status.py" `
    --runtime-root "$env:LOCALAPPDATA\memoriX\runtime" `
    --capacity 50000 `
    --simulate-active-items 6000000 `
    --pretty
```

Simulation never creates the runtime, loads Titan weights, touches the cold
site, validates candidates, or applies pruning.

## Safe pruning workflow

1. Inspect status.
2. Build a dry-run plan.
3. Review recommendations and protected memories.
4. Invoke pruning explicitly with an operator identity and reason.
5. Confirm `pruning_completed` in the operational log.

Only eligible `DEACTIVATE` recommendations are translated into Titan
`soft_forget` operations. Physical deletion is forbidden. Pinned or protected
memories remain active. The cold archive remains untouched.

## Nightly automatic maintenance

While the hot site is expanded, the nightly runner executes capacity
maintenance under a single `mutation_lock("nightly_capacity_maintenance")`:

```text
cold fingerprint -> usage-only pressure -> plan_soft_pruning ->
apply_soft_pruning_plan -> consistency gate -> compact_inactive ->
shrink_to_baseline -> cold fingerprint verify -> record capacity_maintained
```

Automatic soft-forgets use the fixed reviewer `memorix_nightly_capacity` and
are capped by `ElasticCapacityPolicy.max_automatic_deactivations` (200).
Compaction and shrinking are skipped when the consistency gate fails.
Restoration to the baseline happens only at or below
`floor(baseline * 0.80)` active items. The cold archive is fingerprinted
before and after; any change raises `RuntimeError`.

Every maintained run records a `capacity_maintained` event whose payload is
the fixed 12-key report:

```text
capacity_before, capacity_after, active_before, active_after,
automatic_soft_forgets, compaction_attempted, compaction_applied,
shrink_attempted, shrink_applied, shrink_skipped_reason, consistency_ok,
cold_site_modified
```

When the hot site is not expanded the maintenance step is a no-op: no lock,
no event, every counter 0, `capacity_after == capacity_before`.

## Failure handling

A full hot site rejects candidate admission before any Titan write. The
candidate remains pending. A concurrent mutation returns a lock error.
Operational failures must not be bypassed by direct file edits.
