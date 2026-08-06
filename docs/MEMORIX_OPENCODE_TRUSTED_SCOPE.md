# OpenCode trusted scoped memory

Part 44 completes strict project and optional user scoping between OpenCode and memoriX.

## Contract

- The current OpenCode session project ID is injected into the native tool context.
- The optional user namespace is read from `MEMORIX_USER_ID`.
- `memory_store` and `memory_retrieve` do not expose project or user scope fields to the model.
- Native tools pass only the trusted project and configured user to the memory facade.
- The facade, TypeScript service, TypeScript MCP client, Python MCP layer, gateway, and Titan backend preserve these filters.
- Titan applies exact project/user metadata filtering before neural ranking.
- Omitting `MEMORIX_USER_ID` keeps strict project isolation while leaving the user filter unset.

## Configuration

PowerShell example:

```powershell
$env:MEMORIX_USER_ID = "elwen-coroller"
```

Use a stable identifier. Do not use a display name that changes frequently.

## Security property

The language model cannot select another project or user namespace through the native memory tool schema. The project comes from the OpenCode session, and the user comes from trusted process configuration.
