# memoriX Standalone Desktop Application

This package contains the standalone Electron application for **memoriX**, embedding the multi-agent Software Development Life Cycle (SDLC) orchestration runtime (`sdlc`, `dev_branch`, `test_branch`) and deterministic verification gatekeeper (`sdlc-orchestrator`).

## 🚀 Interactive Development

To execute the desktop application from the root monorepo directory with live reloading:
```bash
bun install
bun run desktop
```
*(Or directly from within this module: `bun dev`)*

## 📦 Compiling Standalone Executable Artifacts (`.exe` / `.dmg` / `.AppImage`)

To compile the internal backend sidecar (`virtual:opencode-server`), bundle all required WebAssembly parsers, and generate the self-contained installer distribution:

From the root monorepo directory:
```bash
bun run package:desktop
```
*(Or directly from within this module: `bun run build && bun run package`)*

The resulting executable artifact (e.g., `opencode-desktop-win-x64.exe` for Windows systems) will be synthesized under the `dist/` directory (`packages/desktop/dist/opencode-desktop-win-x64.exe`).
