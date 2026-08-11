<h1 align="center">Memory AGENTX</h1>

<p align="center">
  <em>Design and Evaluation of a Controlled Persistent Memory System for LLM-Based Code Agents</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/language-TypeScript-007ACC?style=flat-square" alt="TypeScript" />
  <img src="https://img.shields.io/badge/language-Python-3776AB?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/runtime-Bun-000000?style=flat-square" alt="Bun" />
  <img src="https://img.shields.io/badge/shell-PowerShell-5391FE?style=flat-square" alt="PowerShell" />
</p>

<p align="center">
  <a href="README.md">English</a> •
  <a href="README.fr.md">Français</a> •
  <a href="README.es.md">Español</a> •
  <a href="README.zh.md">中文</a> •
  <a href="README.ja.md">日本語</a>
</p>

---

## What is MemoriX?

**MemoriX** is an advanced persistent memory system designed specifically for Large Language Model (LLM)-based autonomous coding agents (such as OpenCode). 

As AI agents increasingly assist with complex software development tasks, their continuity across sessions remains fragile. When an agent session terminates, all context—decisions made, constraints discovered, conventions established—usually evaporates. Existing solutions like parametric fine-tuning, vector databases (RAG), or unstructured context dumps fail to provide controlled, auditable, and queryable long-term memory without causing context flooding.

**MemoriX shifts agent memory from a simple storage challenge to a structured knowledge-governance problem.** It provides explicit admission control, logical forgetting, strict project isolation, and safe saturation behavior.

---

## System Architecture

MemoriX draws architectural inspiration from the multi-level structure of human memory. It enforces a strict knowledge lifecycle: **observe → propose → validate → retrieve → update → forget**.

### 1. Short-Term Memory (STM)
A transient journal of recent interactions and events between the agent and the tools. STM serves as an ephemeral buffer; it is **not** queried during normal memory retrieval.

### 2. Cold Site (Historical Archive)
A durable, append-only archive (`events_archive.jsonl`) that stores all events for audit and traceability. It preserves raw history but is strictly quarantined from active reasoning to prevent noise contamination.

### 3. Project Archive
A specialized branch of the Cold Site that stores structured project milestones, architectural decisions, and versioned snapshots at meaningful project boundaries. 

### 4. Candidate Store (The Validation Boundary)
Automation may select and propose information, but admission into active knowledge requires **explicit validation**. The Candidate Store acts as a staging area holding proposed knowledge (`PENDING` state) until it is manually or programmatically validated.

### 5. Titan Hot Site (Active Memory)
The sole active memory system queried during agent retrieval. It is backed by a single Titan neural memory instance. Only validated memories enter the Hot Site. It deduplicates facts, handles logical forgetting (when new memories supersede old ones), and groups memories into thematic blocks.

---

## Tech Stack & Integration

MemoriX maintains a clean runtime boundary using the **Model Context Protocol (MCP)** via JSON-RPC over `stdio`. 

- **Orchestration Layer (TypeScript / Bun)**: Manages agent lifecycle, Software Development Life Cycle (SDLC) workflows, and communicates with the memory subsystem via MCP.
- **Memory Subsystem (Python 3.10+)**: Handles the Titan neural memory backend, consolidation pipelines, and storage management.

The system natively supports a **Multi-Agent SDLC Workflow**, delegating tasks among specialized agents:
- `sdlc`: Architect/Orchestrator (PRD/SRS, planning, delegation).
- `dev_branch`: Implementation within the development scope.
- `test_branch`: Independent testing and validation.

---

## Key Benchmarks & Performance

MemoriX was evaluated rigorously through a paired A/B benchmark (2,048 runs across 32 task families using `qwen2.5:3b`).

### 1. Overall A/B Benchmark Results

| Metric | No-Memory | MemoriX | Δ |
| ------ | --------- | ------- | - |
| **Overall Pass Rate** | 31.9% (327/1024) | 60.0% (614/1024) | **+28.0pp** |
| **Median Family Latency** | 3,384 ms | 3,504 ms | +120 ms |
| **Families Evaluated** | 32 | 32 | — |
| **Families Won** (Δ > 0) | — | 12 | — |
| **Families Lost** (Δ < 0) | — | 4 | — |

### 2. Multi-Agent SDLC Workflow

Evaluates task success across distinct agent roles while strictly preventing information leakage.

| Metric | No-Memory | MemoriX | Delta |
| ------ | --------- | ------- | ----- |
| **Task Success Rate** | 25.0% | 37.5% | **+12.5pp** |
| **Forbidden-Information Use** | 0.0% | 0.0% | **Perfect Isolation** |
| **Tool Calls** | 5,000 | 8,750 | — |
| **Mean Response** | N/A | 257.3 ms | — |

### 3. BFCL-Derived Retrieval (Blind Curation)

Independent evaluation of the retrieval quality mechanism on a 125-pair dataset.

| Stage | Result | Rate |
| ----- | ------ | ---- |
| Correct baseline | 0/125 | 0% |
| Curated corpus contains reference | 125/125 | 100% |
| Retrieval contains reference | 96/125 | **76.8%** |
| Correct final answer | 96/125 | **76.8%** |

### 4. Capacity Saturation Behavior

Testing the memory system's reaction to increasing load and extreme overload.

| Active Items | Admission Allowed | Pressure Level | Usage Ratio | Decision Latency |
| ------------ | ----------------- | -------------- | ----------- | ---------------- |
| 10,000 | ✅ | stable | 0.2 | 0.0013 ms |
| **50,000** | ❌ | **critical** | **1.0** | **0.0009 ms** |
| 500,000 | ❌ | critical | 10.0 | 0.0024 ms |
| 6,000,000 | ❌ | critical | 120.0 | 0.0023 ms |

*Note: MemoriX elegantly rejects overflow (❌) instead of silently overwriting existing memories once the 50,000 capacity boundary is hit, all while maintaining sub-millisecond decision latency.*

---

## Complete Installation Guide (From A to Z)

This guide will walk you through installing MemoriX and OpenCode from scratch. It is designed to be accessible even if you are completely new to these tools.

### Step 1: Prerequisites

Before starting, ensure you have the following installed on your machine:

1. **Git**: Used to download the source code.
   - Download & Install: [git-scm.com](https://git-scm.com/)
2. **Node.js & Bun**: Bun is a fast all-in-one JavaScript runtime used to run the OpenCode interface.
   - Download Node.js (required by some plugins): [nodejs.org](https://nodejs.org/)
   - Install Bun: Open your terminal (PowerShell) and run:
     ```powershell
     powershell -c "irm bun.sh/install.ps1 | iex"
     ```
3. **Python 3.10 or higher**: Required for the Titan memory backend.
   - Download & Install: [python.org](https://www.python.org/downloads/)
   - **Important**: During installation, make sure to check the box **"Add Python to PATH"**.

### Step 2: Clone the Repository

Open your terminal (PowerShell recommended) and download the MemoriX source code:

```powershell
# Navigate to the folder where you want to install it
cd C:\Your\Preferred\Folder

# Clone the repository
git clone https://github.com/anomalyco/memoriX.git

# Enter the directory
cd memoriX
```

### Step 3: Install JavaScript Dependencies

Use Bun to install all necessary packages for the workspace:

```powershell
bun install
```
*(This may take a few moments depending on your connection.)*

### Step 4: Verify Python Environment

The system requires Python 3. To verify everything is set up correctly, MemoriX includes a pre-validation script. Run it with the following command:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1 -ValidateOnly
```
**Expected Output:**
You should see messages indicating `MemoriXGateway import OK` and a summary of your configuration. If you see an error about Python missing, ensure Python is installed and added to your PATH.

### Step 5: Start the System!

Once validation passes, you can launch the full OpenCode interface with MemoriX memory enabled:

```powershell
.\tools\memorix\runtime\start_opencode_with_memorix.ps1
```
This script acts as the bridge: it launches the MCP server in the background and starts the OpenCode interface. You are now ready to code with an agent that *actually remembers*.

---

## Advanced Operations

MemoriX includes several advanced tools for maintenance and Windows integration located in `tools/memorix/operations`:

- **Nightly Consolidation**: `run_memorix_nightly.ps1` runs background consolidation and capacity maintenance.
- **Global Command**: `install_memorix_opencode_command.ps1` registers MemoriX globally on your system.
- **Backup & Restore**: `memorix_runtime_backup.py` and `memorix_runtime_restore.py` allow you to safely backup your agent's neural memory.

---

## Additional Documentation
- [Detailed Architecture](docs/MEMORIX_FINAL_ARCHITECTURE.md)
- [Operations Manual](docs/MEMORIX_OPERATIONS.md)
