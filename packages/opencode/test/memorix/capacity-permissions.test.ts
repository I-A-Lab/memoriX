import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const source = readFileSync(
  join(import.meta.dir, "../../src/tool/memory-capacity.ts"),
  "utf8",
)

describe("capacity native permissions", () => {
  test("pruning asks before calling the facade", () => {
    const start = source.indexOf('"memory_capacity_prune"')
    const value = source.slice(start)

    expect(start).toBeGreaterThanOrEqual(0)
    expect(value.indexOf("ctx.ask")).toBeLessThan(
      value.indexOf("pruneCapacity("),
    )
    expect(value).toContain(
      'permission: "memory_capacity_prune"',
    )
  })

  test("read-only capacity tools do not ask", () => {
    const statusStart = source.indexOf('"memory_capacity_status"')
    const planStart = source.indexOf('"memory_capacity_plan"')
    const pruneStart = source.indexOf('"memory_capacity_prune"')

    expect(source.slice(statusStart, planStart)).not.toContain("ctx.ask")
    expect(source.slice(planStart, pruneStart)).not.toContain("ctx.ask")
  })

  test("permissions are configured safely", () => {
    const config = readFileSync(
      join(import.meta.dir, "../../../../.opencode/opencode.jsonc"),
      "utf8",
    )

    expect(config).toContain('"memory_capacity_status": "allow"')
    expect(config).toContain('"memory_capacity_plan": "allow"')
    expect(config).toContain('"memory_capacity_prune": "ask"')
  })
})
