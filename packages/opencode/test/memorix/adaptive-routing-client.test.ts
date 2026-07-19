import { describe, expect, test } from "bun:test"
import { MemoriXClient, type JSONObject, type JSONValue, type MemoriXToolName } from "../../src/memorix"

describe("adaptive routing TypeScript contract", () => {
  test("client forwards the read-only routing plan", async () => {
    const client = Object.create(MemoriXClient.prototype) as MemoriXClient
    const calls: Array<{ name: MemoriXToolName; args: JSONObject }> = []
    client.callTool = async <T extends JSONValue = JSONValue>(name: MemoriXToolName, args: JSONObject = {}): Promise<T> => { calls.push({ name, args }); return { status: "ok" } as unknown as T }
    await client.adaptiveRoutingPlan({ target_id: "candidate-1", retention_score: 0.9 })
    expect(calls).toEqual([{ name: "memorix_adaptive_routing_plan", args: { target_id: "candidate-1", retention_score: 0.9 } }])
  })
})
