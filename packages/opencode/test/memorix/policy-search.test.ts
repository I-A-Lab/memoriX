import { expect, test } from "bun:test"
import { getPolicySearch } from "../../src/memorix/policy-search-facade"
test("policy search facade preserves dry-run report", async () => {
  const result = await getPolicySearch({ policySearch: async () => ({ ok: true, value: { dry_run: true, policy_applied: false } }) }, {})
  expect(result.metadata.ok).toBe(true)
  expect(result.output).toContain("policy_applied")
})
