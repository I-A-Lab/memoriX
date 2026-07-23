
import { expect, test } from "bun:test"
import { runPolicyLifecycle } from "../../src/memorix"
test("policy lifecycle facade returns report", async () => {
  const service = { policyLifecycle: async () => ({ ok: true as const, value: { action: "inspect", registry_exists: false } }) }
  const result = await runPolicyLifecycle(service as any, { action: "inspect" })
  expect(result.metadata.ok).toBe(true)
})
