# memoriX Adaptive Memory — Part 12A Inventory and Contracts

## 1. Scope

Part 12 reintroduces adaptive hot-site memory capabilities:

- memory pressure metrics;
- dynamic topic blocks;
- block routing;
- dynamic capacity recommendations;
- hot-site soft pruning;
- adaptive design benchmarks;
- a live diagnostic probe.

Part 12 must adapt these capabilities to the current gateway and storage
contracts. Legacy files must not be copied or activated blindly.

## 2. Non-negotiable architecture contracts

### 2.1 Cold site

The cold site is complete durable history.

Adaptive components must not:

- prune cold records;
- deactivate cold records;
- route cold records into topic blocks;
- use cold history as an automatic retrieval fallback;
- automatically rehydrate the hot site from cold history;
- use cold history as the source of expansion or pruning actions.

Cold history may be inspected only through an explicit audit operation.

### 2.2 Hot site

The hot site contains active, human-validated external memories.

Adaptive components may observe and plan actions for the hot site, but they
must preserve:

- human validation before hot-site insertion;
- hot-only retrieval;
- logical memory identity;
- metadata from the validated candidate;
- soft-forget rather than physical deletion.

### 2.3 Short-term memory

Short-term events may contribute to observation windows and consolidation.

They must still be archived directly to the cold site before any adaptive
routing or consolidation decision.

### 2.4 Candidates

Topic routing and adaptive metrics may annotate or recommend a target block
for a pending candidate.

They must not validate a candidate automatically.

### 2.5 OpenCode and MCP

Part 12 must not change the public meaning of:

- memory_store;
- memory_retrieve;
- memorix_context;
- memorix_search_cold_history.

New adaptive information must initially be exposed only through explicit
status, diagnostics, benchmark or probe interfaces.

## 3. Safety rollout

The activation order is:

1. observable metrics only;
2. observable dynamic topic blocks;
3. controlled routing metadata;
4. expansion recommendations in dry-run;
5. pruning plans in dry-run;
6. explicitly enabled adaptive actions;
7. benchmark and live probe.

No adaptive action may be enabled merely because a metric exists.

## 4. Persistence

Adaptive state must use MemoryStoragePaths.

Legacy standalone JSON paths must not be reused directly.

Proposed future paths:

- adaptive/pressure_history.jsonl
- adaptive/topic_blocks.json
- adaptive/action_plans.jsonl
- adaptive/benchmark_runs/
- adaptive/live_probe_runs/

These paths are design proposals only during Part 12A.

## 5. Legacy component classification

### memory_pressure.py

Status: reusable after light adaptation.

The mathematical functions are mostly pure. Their output must be separated
from any expansion or pruning action.

### topic_blocks.py

Status: algorithms reusable; legacy persistence must be replaced.

Blocks remain dynamic and content-driven. No fixed domain list is allowed.

### pruning.py

Status: scoring logic reusable; action application must be rewritten.

Initial mode must be dry-run and hot-site only.

### design_benchmark.py

Status: reusable after pressure, blocks, capacity and pruning exist.

It must run on temporary isolated runtimes.

### live_probe.py

Status: concept retained; implementation must be rewritten.

It must use MemoriXGateway only and must not import the former memory_tools or
titan_agent_memory modules.

## 6. Planned modules

- memory/adaptive/contracts.py
- memory/adaptive/pressure.py
- memory/adaptive/pressure_history.py
- memory/adaptive/topic_blocks.py
- memory/adaptive/block_registry.py
- memory/adaptive/routing.py
- memory/adaptive/capacity.py
- memory/adaptive/pruning.py
- memory/adaptive/controller.py
- memory/benchmark/adaptive_designs.py
- memory/observability/live_probe.py

Only this document is created during Part 12A. Runtime modules begin in Part
12B.

## 7. Current activation status

| Component | Current status after 12A |
|---|---|
| Pressure metrics | Design reviewed, not integrated |
| Topic blocks | Design reviewed, not integrated |
| Block routing | Design only |
| Dynamic capacity | Design only |
| Pruning | Design reviewed, dry-run not yet integrated |
| Adaptive controller | Not implemented |
| Benchmark | Legacy design reviewed, not integrated |
| Live probe | Legacy concept reviewed, not integrated |

## 8. Definition of done for Part 12A

Part 12A is complete when:

- all legacy adaptive files have been located and hashed;
- their imports and public declarations have been inventoried;
- obsolete dependencies have been identified;
- the current hot/cold contracts have been verified;
- this document has been reviewed;
- no runtime memory code has been changed.
