import { describe, expect, test } from "bun:test"
import { runObservability } from "../../src/memorix/observability-facade"
describe("observability facade", () => {
  test("returns report", async () => {
    const service = { observability: async () => ({ ok: true as const, value: { status: "healthy" } }) }
    const result = await runObservability(service as any, { action: "report" })
    expect(result.metadata.ok).toBe(true)
  })
})
