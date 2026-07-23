import { describe, expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { join } from "node:path"
const source = readFileSync(join(import.meta.dir, "../../src/tool/memory-pressure.ts"), "utf8")

describe("memory pressure native permissions", () => {
  test("pressure tools are read-only", () => { expect(source).not.toContain("ctx.ask") })
  test("permissions are configured as allow", () => {
    const config = readFileSync(join(import.meta.dir, "../../../../.opencode/opencode.jsonc"), "utf8")
    expect(config).toContain('"memory_pressure_status": "allow"')
    expect(config).toContain('"memory_pressure_inspect": "allow"')
  })
})
