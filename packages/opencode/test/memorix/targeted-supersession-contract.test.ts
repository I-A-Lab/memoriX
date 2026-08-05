import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const projectRoot = process.env.MEMORIX_OPENCODE_ROOT

if (!projectRoot) {
  throw new Error(
    "MEMORIX_OPENCODE_ROOT is required",
  )
}

function read(relativePath: string) {
  return readFileSync(
    join(projectRoot, relativePath),
    "utf8",
  )
}

function extractToolBlock(
  source: string,
  toolID: string,
  nextToolID?: string,
) {
  const startMarker = `"${toolID}"`
  const start = source.indexOf(startMarker)

  expect(start).toBeGreaterThanOrEqual(0)

  if (!nextToolID) {
    return source.slice(start)
  }

  const end = source.indexOf(
    `"${nextToolID}"`,
    start + startMarker.length,
  )

  expect(end).toBeGreaterThan(start)

  return source.slice(start, end)
}

describe("memoriX targeted supersession contract", () => {
  const candidateTool = read(
    "src/tool/memory-candidates.ts",
  )
  const service = read("src/memorix/service.ts")
  const types = read("src/memorix/types.ts")
  const registry = read("src/tool/registry.ts")

  test("candidate validation accepts an exact superseded memory ID", () => {
    const block = extractToolBlock(
      candidateTool,
      "memory_candidate_validate",
      "memory_candidate_reject",
    )

    expect(candidateTool).toContain(
      "supersedes_memory_id",
    )
    expect(block).toContain(
      "params.supersedes_memory_id",
    )
    expect(block).toContain(
      "supersedesMemoryID:",
    )
    expect(block).toContain(
      "supersedes_memory_id:",
    )
  })

  test("service validation forwards supersedes_memory_id to MCP", () => {
    expect(types).toContain(
      "supersedes_memory_id",
    )
    expect(service).toContain(
      "supersedesMemoryID",
    )
    expect(service).toContain(
      "supersedes_memory_id:",
    )
    expect(service).toContain(
      "memorix_validate_candidate",
    )
  })

  test("a native exact-ID memory_forget tool is exposed", () => {
    expect(candidateTool).toContain(
      '"memory_forget"',
    )

    const block = extractToolBlock(
      candidateTool,
      "memory_forget",
      "memory_consolidate",
    )

    expect(block).toContain(
      "memory_id",
    )
    expect(block).toContain(
      "validated_by",
    )
    expect(block).toContain(
      "reason",
    )
    expect(block).toContain(
      'permission: "memory_forget"',
    )
    expect(block).toContain(
      "patterns: [params.memory_id]",
    )
    expect(block).toContain(
      "forgetMemoryThroughMemoriX(",
    )
  })

  test("service and type contracts expose exact-ID forgetting", () => {
    expect(types).toContain(
      "MemoriXForget",
    )
    expect(service).toContain(
      "forgetMemory",
    )
    expect(service).toContain(
      "memorix_forget_memory",
    )
    expect(service).toContain(
      "memory_id:",
    )
    expect(service).toContain(
      "validated_by:",
    )
    expect(service).toContain(
      "reason:",
    )
  })

  test("the native memory_forget tool is registered", () => {
    expect(registry).toContain(
      "MemoryForgetTool",
    )
  })
})
