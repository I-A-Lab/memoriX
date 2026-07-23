import { describe, expect, test } from "bun:test"
import { readFile } from "node:fs/promises"

describe("retention ranking native permissions", () => {
  test("retention tools are read-only", async () => {
    const source = await readFile(
      new URL(
        "../../src/tool/retention-ranking.ts",
        import.meta.url,
      ),
      "utf8",
    )
    expect(source.includes("ctx.ask")).toBe(false)
  })

  test("permissions are configured as allow", async () => {
    const source = await readFile(
      new URL(
        "../../../../.opencode/opencode.jsonc",
        import.meta.url,
      ),
      "utf8",
    )
    expect(source).toContain(
      '"retention_ranking_status": "allow"',
    )
    expect(source).toContain(
      '"retention_ranking_inspect": "allow"',
    )
  })
})
