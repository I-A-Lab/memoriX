# memoriX Agent Multi-Session Benchmark

This benchmark isolates persistent-memory reuse across two sessions. Session 1 ingests the dataset. Session 2 starts with an empty conversational context and asks the dataset queries.

Modes:
- `no_memory`: session-only context is cleared before evaluation.
- `memorix_core`: facts persist through either the deterministic lexical control backend or the real memoriX gateway.

The lexical backend validates the experiment and metrics. The memoriX backend is a smoke test of the real gateway. A single run must not be presented as a final scientific conclusion.

Generated reports must remain outside the repository and are immutable.
