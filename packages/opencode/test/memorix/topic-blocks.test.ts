
import { expect, test } from "bun:test"
import { runTopicBlocks } from "../../src/memorix"
test("topic blocks facade returns report", async () => {
  const service = { topicBlocks: async () => ({ ok: true as const, value: { action: "inspect", blocks: [] } }) }
  const result = await runTopicBlocks(service as any, { action: "inspect" })
  expect(result.metadata.ok).toBe(true)
})
