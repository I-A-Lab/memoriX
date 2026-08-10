# MEMORY AGENTX
<p align="center">Autonomous coding agent system based on a persistent long-term memory architecture.</p>

---

## Introduction

**memoriX** is an artificial intelligence-driven software development agent designed to operate within a persistent memory architecture. Unlike stateless generation models, memoriX implements a comprehensive orchestration of the Software Development Life Cycle (SDLC). It relies on the Titan memory engine and the Model Context Protocol (MCP) to deterministically manage cognitive load, context retention, and information retrieval over extended development sessions.

## Core Features

- **Multi-Agent SDLC Orchestration**: The system relies on a distributed architecture of isolated specialized agents (`sdlc`, `dev_branch`, `test_branch`, `sdlc-orchestrator`). These agents collaborate via strict contracts to validate specifications, implement logic, and generate tests deterministically.
- **Adaptive Memory Retention (Titan)**: Implementation of an intelligent persistence system including adaptive retention scoring, allowing controlled pruning and consolidation of data without loss of contextual integrity.
- **Dynamic Data Structuring**: Unsupervised classification of context into thematic blocks, facilitating selective access and reducing information noise.
- **State Analysis and Observability**: Integration of real-time diagnostic tools to evaluate memory saturation and pressure (capacity tested up to several million active nodes) without degrading the performance of the primary process.

## Specifications and Prerequisites

Executing the system from the source code requires the following environment:
- **Bun** (v1.3 or higher): Required for package management and monorepo execution.
- **Python** (v3.10 or higher): Required for the Titan memory engine and underlying analysis processes.
- **Execution Environment**: PowerShell (recommended environment for Windows systems).

## Installation Procedure (Compilation from source)

1. **Cloning the source repository**
   ```bash
   git clone https://github.com/anomalyco/memoriX.git
   cd memoriX
   ```

2. **Dependency Resolution**
   The monorepo architecture requires the installation of modules via Bun:
   ```bash
   bun install
   ```

## Runtime Execution

To initialize the execution environment, establish the connection to the MCP server, and launch the primary orchestration loop, execute the following bootstrap script:

```powershell
.\scripts\start_opencode_with_memorix.ps1
```

*(Technical note: This script performs security validations on the execution environment to ensure strict isolation between the agent's memory space and the application's source code.)*

## Global Installation (Pre-compiled binaries)

For utilizing memoriX as a global system tool without local compilation, the following methods are supported:

```bash
# Automated installation (POSIX Environments)
curl -fsSL https://memorix.ai/install | bash

# Installation via package managers
npm i -g memorix@latest        # Alternative: bun / pnpm / yarn
brew install memorix           # macOS (via Homebrew)
scoop install memorix          # Windows (via Scoop)
```

## Memory System Architecture

The architecture of memoriX enforces a strict separation between the presentation layer (user interface) and the memory management daemon. The conceptual model is divided into several components:

- **Hot-Site (Short-Term Memory)**: Space allocated to maintaining the active session context, optimized for minimal latency.
- **Cold-Site (Long-Term Memory)**: Persistence space dedicated to archiving, consolidation, and adaptive routing (interfaced via MCP).
- **Eviction Policies**: Deterministic scoring algorithms preventing the saturation of the Large Language Model (LLM) context window.

For comprehensive documentation of the architecture and its protocols, please consult the reference documents:
- [Detailed Architecture](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Operations Manual](docs/MEMORIX_OPERATIONS.md)
