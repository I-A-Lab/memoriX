# OpenCode explicit scoped-memory transport

Part 44A adds explicit `project_id` and `user_id` parameters to the native
OpenCode `memory_store` and `memory_retrieve` tools.

The values are propagated through:

1. the native tool schema;
2. the memory facade;
3. `MemoriXService`;
4. `MemoriXClient`;
5. the existing Python MCP `memorix_context` contract.

This stage deliberately does not infer the current project or user. Automatic
trusted scope resolution is deferred to Part 44B, after explicit transport has
passed typecheck and focused tests.

Storage behavior:

- `project_id` is written to the event's top-level project field;
- `project_id` and `user_id` are copied into event and candidate metadata.

Retrieval behavior:

- both filters remain optional;
- omitted filters preserve the pre-Part-44 global behavior;
- provided filters are sent to the Python MCP server as strict namespace
  filters implemented in Part 43.
