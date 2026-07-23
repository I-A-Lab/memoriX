import { describe, expect, test } from "bun:test"
import { readFile } from "node:fs/promises"

describe("adaptive routing permissions", () => {
  test("tool is read-only", async () => {
    const source = await readFile(new URL("../../src/tool/adaptive-routing.ts", import.meta.url), "utf8")
    expect(source.includes("ctx.ask")).toBe(false)
  })
  test("permission is allow", async () => {
    const source = await readFile(new URL("../../../../.opencode/opencode.jsonc", import.meta.url), "utf8")
    expect(source).toContain('"adaptive_routing_plan": "allow"')
  })
})
