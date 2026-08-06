import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const projectRoot = join(import.meta.dir, "../..")
const memoryToolPath = join(projectRoot, "src/tool/memory.ts")
const candidateToolPath = join(
  projectRoot,
  "src/tool/memory-candidates.ts",
)

function read(path: string) {
  return readFileSync(path, "utf8")
}

function extractToolBlock(
  source: string,
  toolID: string,
  nextToolID?: string,
) {
  const startMarker = `"${toolID}"`
  const start = source.indexOf(startMarker)

  if (start < 0) {
    throw new Error(`Tool not found: ${toolID}`)
  }

  if (!nextToolID) {
    return source.slice(start)
  }

  const end = source.indexOf(`"${nextToolID}"`, start + startMarker.length)

  if (end < 0) {
    throw new Error(
      `Next tool not found after ${toolID}: ${nextToolID}`,
    )
  }

  return source.slice(start, end)
}

function expectProtectedMutation(
  block: string,
  permission: string,
  operationCall: string,
) {
  const askIndex = block.indexOf("yield* ctx.ask({")
  const permissionIndex = block.indexOf(
    `permission: "${permission}"`,
  )
  const alwaysIndex = block.indexOf("always: []")
  const operationIndex = block.indexOf(operationCall)

  expect(askIndex).toBeGreaterThanOrEqual(0)
  expect(permissionIndex).toBeGreaterThan(askIndex)
  expect(alwaysIndex).toBeGreaterThan(permissionIndex)
  expect(operationIndex).toBeGreaterThan(alwaysIndex)

  expect(
    block.match(
      new RegExp(
        `permission: "${permission}"`,
        "g",
      ),
    )?.length ?? 0,
  ).toBe(1)
}

describe("memoriX native mutation permissions", () => {
  const memorySource = read(memoryToolPath)
  const candidateSource = read(candidateToolPath)

  test("memory_store asks before calling the memoriX facade", () => {
    const block = extractToolBlock(
      memorySource,
      "memory_store",
      "memory_retrieve",
    )

    expectProtectedMutation(
      block,
      "memory_store",
      "storeMemoryThroughMemoriX(",
    )
    expect(block).toContain(
      'operation: "create_pending_candidate"',
    )
    expect(block).toContain(
      "patterns: [params.subject]",
    )
  })

  test("memory_candidate_validate asks before validation", () => {
    const block = extractToolBlock(
      candidateSource,
      "memory_candidate_validate",
      "memory_candidate_reject",
    )

    expectProtectedMutation(
      block,
      "memory_candidate_validate",
      "validateCandidateThroughMemoriX(",
    )
    expect(block).toContain(
      'operation: "validate_candidate"',
    )
    expect(block).toContain(
      "params.candidate_id,",
    )
    expect(block).toContain(
      "params.supersedes_memory_id",
    )
  })

  test("memory_forget asks before forgetting", () => {
    const block = extractToolBlock(
      candidateSource,
      "memory_forget",
      "memory_consolidate",
    )

    expectProtectedMutation(
      block,
      "memory_forget",
      "forgetMemoryThroughMemoriX(",
    )
    expect(block).toContain(
      'operation: "forget_memory"',
    )
    expect(block).toContain(
      "patterns: [params.memory_id]",
    )
  })

  test("memory_candidate_reject asks before rejection", () => {
    const block = extractToolBlock(
      candidateSource,
      "memory_candidate_reject",
      "memory_consolidate",
    )

    expectProtectedMutation(
      block,
      "memory_candidate_reject",
      "rejectCandidateThroughMemoriX(",
    )
    expect(block).toContain(
      'operation: "reject_candidate"',
    )
    expect(block).toContain(
      "patterns: [params.candidate_id]",
    )
  })

  test("memory_consolidate asks before consolidation", () => {
    const block = extractToolBlock(
      candidateSource,
      "memory_consolidate",
      "memory_status",
    )

    expectProtectedMutation(
      block,
      "memory_consolidate",
      "runConsolidationThroughMemoriX(",
    )
    expect(block).toContain(
      'operation: "run_consolidation"',
    )
    expect(block).toContain("patterns: [mode]")
  })

  test("read-only tools do not request mutation permissions", () => {
    const retrieveBlock = extractToolBlock(
      memorySource,
      "memory_retrieve",
    )
    const listBlock = extractToolBlock(
      candidateSource,
      "memory_candidates_list",
      "memory_candidate_validate",
    )
    const statusBlock = extractToolBlock(
      candidateSource,
      "memory_status",
    )

    expect(retrieveBlock).not.toContain("ctx.ask")
    expect(listBlock).not.toContain("ctx.ask")
    expect(statusBlock).not.toContain("ctx.ask")
  })
})
