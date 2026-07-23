import path from "node:path"
import os from "node:os"
import { mkdtemp, rm } from "node:fs/promises"

import {
  MemoriXClient,
  type JSONObject,
  type JSONValue,
} from "../src/memorix"

function assertCondition(
  condition: unknown,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message)
  }
}

function asObject(
  value: JSONValue,
  label: string,
): JSONObject {
  assertCondition(
    typeof value === "object" &&
      value !== null &&
      !Array.isArray(value),
    `${label} must be an object.`,
  )

  return value as JSONObject
}

function asString(
  value: JSONValue | undefined,
  label: string,
): string {
  assertCondition(
    typeof value === "string" && value.length > 0,
    `${label} must be a non-empty string.`,
  )

  return value
}

function asArray(
  value: JSONValue | undefined,
  label: string,
): JSONValue[] {
  assertCondition(
    Array.isArray(value),
    `${label} must be an array.`,
  )

  return value
}

async function cleanupRuntime(
  runtimeRoot: string,
): Promise<void> {
  await rm(runtimeRoot, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 100,
  })
}

async function main(): Promise<void> {
  const pythonExecutable =
    process.env.MEMORIX_PYTHON_EXECUTABLE?.trim()

  assertCondition(
    pythonExecutable,
    "MEMORIX_PYTHON_EXECUTABLE is required.",
  )

  const repositoryRoot = path.resolve(
    import.meta.dir,
    "../../..",
  )

  const runtimeRoot = await mkdtemp(
    path.join(
      os.tmpdir(),
      "memorix-opencode-integration-",
    ),
  )

  const client = new MemoriXClient({
    pythonExecutable,
    projectRoot: repositoryRoot,
    runtimeRoot,
    timeoutMs: 30_000,
    titanDModel: 32,
    titanHiddenDim: 32,
    titanMaxItems: 100,
    titanDevice: "cpu",
    titanTopK: 5,
    titanMinScore: 0.0,
  })

  console.log("[1/10] Connecting to memoriX MCP...")

  try {
    await client.connect()

    assertCondition(
      client.connected,
      "Client should be connected after connect().",
    )

    console.log("[2/10] Listing MCP tools...")

    const tools = await client.listTools()
    const toolNames = tools.map((tool) => tool.name)

    const expectedTools = [
      "memorix_record_event",
      "memorix_context",
      "memorix_search_cold_history",
      "memorix_propose_candidate",
      "memorix_list_candidates",
      "memorix_validate_candidate",
      "memorix_reject_candidate",
      "memorix_forget_memory",
      "memorix_run_consolidation",
      "memorix_run_nightly",
      "memorix_status",
    ]

    assertCondition(
      tools.length === expectedTools.length,
      `Expected ${expectedTools.length} MCP tools, received ${tools.length}.`,
    )

    for (const expectedTool of expectedTools) {
      assertCondition(
        toolNames.includes(expectedTool),
        `Missing MCP tool: ${expectedTool}`,
      )
    }

    console.log("[3/10] Reading memoriX status...")

    const initialStatus = await client.status()

    assertCondition(
      initialStatus.retrieval_contract ===
        "hot_site_only_no_cold_fallback",
      "Invalid hot-site retrieval contract.",
    )

    assertCondition(
      initialStatus.cold_site_contract ===
        "explicit_audit_history_only",
      "Invalid cold-site audit contract.",
    )

    assertCondition(
      initialStatus.automatic_rehydration === false,
      "Automatic rehydration must remain disabled.",
    )

    console.log(
      "[4/10] Recording one short-term/cold event...",
    )

    await client.recordEvent({
      content:
        "TypeScript MCP cold-only token TS-MCP-COLD-7319.",
      event_type: "architecture_rule",
      source: "opencode_integration_test",
      project_id: "memorix",
      session_id: "session_typescript_mcp",
      importance: 0.95,
      confidence: 1.0,
      surprise: 0.6,
      metadata: {
        integration_test: true,
      },
    })

    console.log(
      "[5/10] Verifying hot retrieval has no cold fallback...",
    )

    const coldOnlyHotResult = await client.context(
      "TS-MCP-COLD-7319",
    )

    assertCondition(
      coldOnlyHotResult.source === "hot_site",
      "memorix_context did not use the hot site.",
    )

    assertCondition(
      coldOnlyHotResult.matches.length === 0,
      "Cold-only information unexpectedly appeared in hot retrieval.",
    )

    console.log(
      "[6/10] Verifying explicit cold audit search...",
    )

    const coldAuditResult =
      await client.searchColdHistory(
        "TS-MCP-COLD-7319",
      )

    assertCondition(
      coldAuditResult.source === "cold_audit",
      "Cold search did not use cold_audit.",
    )

    assertCondition(
      coldAuditResult.matches.length === 1,
      `Expected one cold result, received ${coldAuditResult.matches.length}.`,
    )

    assertCondition(
      coldAuditResult.matches[0]?.metadata
        .automatic_rehydration === false,
      "Cold result unexpectedly permits automatic rehydration.",
    )

    console.log(
      "[7/10] Creating a pending candidate...",
    )

    const candidateValue = await client.callTool(
      "memorix_propose_candidate",
      {
        content:
          "Validated TypeScript MCP memory belongs to the Titan hot site.",
        reason:
          "TypeScript-to-Python MCP integration validation.",
        source_event_ids: [
          "event_typescript_candidate_001",
        ],
        importance: 0.95,
        confidence: 1.0,
        surprise: 0.7,
        metadata: {
          integration_test: true,
        },
      },
    )

    const candidate = asObject(
      candidateValue,
      "Candidate response",
    )

    const candidateID = asString(
      candidate.candidate_id,
      "candidate_id",
    )

    assertCondition(
      candidate.status === "pending",
      "New candidate must be pending.",
    )

    console.log(
      "[8/10] Human-validating candidate into Titan...",
    )

    const memoryValue = await client.callTool(
      "memorix_validate_candidate",
      {
        candidate_id: candidateID,
        validated_by: "typescript_integration_reviewer",
        validation_reason:
          "Approved during the TypeScript MCP integration test.",
      },
    )

    const memory = asObject(
      memoryValue,
      "Validated-memory response",
    )

    const memoryID = asString(
      memory.memory_id,
      "memory_id",
    )

    console.log(
      "[9/10] Retrieving validated Titan memory...",
    )

    const hotResult = await client.context(
      "Validated TypeScript MCP memory Titan hot site",
    )

    assertCondition(
      hotResult.source === "hot_site",
      "Validated-memory retrieval did not use hot_site.",
    )

    assertCondition(
      hotResult.matches.length >= 1,
      "Validated memory was not returned by Titan.",
    )

    assertCondition(
      hotResult.matches.some(
        (match) => match.memory_id === memoryID,
      ),
      "Validated memory ID was not found in retrieval results.",
    )

    console.log(
      "[10/10] Checking final persistent state...",
    )

    const finalStatus = await client.status()

    assertCondition(
      finalStatus.short_term_events === 1,
      `Expected one short-term event, received ${finalStatus.short_term_events}.`,
    )

    assertCondition(
      finalStatus.cold_archive_events === 1,
      `Expected one cold event, received ${finalStatus.cold_archive_events}.`,
    )

    assertCondition(
      finalStatus.candidates.validated === 1,
      `Expected one validated candidate, received ${finalStatus.candidates.validated}.`,
    )

    assertCondition(
      finalStatus.hot_memories_active === 1,
      `Expected one active hot memory, received ${finalStatus.hot_memories_active}.`,
    )

    const listedCandidates = await client.callTool(
      "memorix_list_candidates",
      {
        status: "validated",
      },
    )

    const candidateList = asArray(
      listedCandidates,
      "Validated candidate list",
    )

    assertCondition(
      candidateList.length === 1,
      `Expected one validated candidate, received ${candidateList.length}.`,
    )

    console.log("")
    console.log(
      "memoriX TypeScript/Python integration: OK",
    )
    console.log(`Candidate: ${candidateID}`)
    console.log(`Memory: ${memoryID}`)
    console.log(
      "Contract: hot-only retrieval / explicit cold audit",
    )
  } finally {
    console.log("Closing memoriX client...")

    await client.close()

    assertCondition(
      client.connected === false,
      "Client should be disconnected after close().",
    )

    await cleanupRuntime(runtimeRoot)

    console.log(
      "Temporary memoriX runtime removed.",
    )
  }
}

await main()
