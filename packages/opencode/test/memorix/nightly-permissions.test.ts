import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const source = readFileSync(
  join(import.meta.dir, "../../src/tool/memory-candidates.ts"),
  "utf8",
)

describe("nightly native permission", () => {
  test("asks before running the nightly facade", () => {
    const start = source.indexOf('"memory_nightly_run"')
    const end = source.indexOf("export const MemoryStatusTool", start)
    const value = source.slice(start, end)

    expect(start).toBeGreaterThanOrEqual(0)
    expect(value.indexOf("ctx.ask")).toBeLessThan(
      value.indexOf("runNightlyThroughMemoriX("),
    )
    expect(value).toContain('permission: "memory_nightly_run"')
    expect(value).toContain("clear_short_term_after_success")
  })

  test("is configured as ask", () => {
    const config = readFileSync(
      join(import.meta.dir, "../../../../.opencode/opencode.jsonc"),
      "utf8",
    )

    expect(config).toContain('"memory_nightly_run": "ask"')
  })
})
