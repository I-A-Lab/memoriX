import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXClient,
  MemoriXService,
  getCapacityStatus,
  type JSONObject,
  type JSONValue,
  type MemoriXToolName,
} from "../../src/memorix"

const projectRoot = path.resolve(import.meta.dir, "../../../..")

describe("capacity TypeScript contract", () => {
  test("client forwards bounded capacity operations", async () => {
    const client = new MemoriXClient({
      pythonExecutable: process.execPath,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "capacity-client"),
    })
    const calls: Array<{ name: MemoriXToolName; arguments: JSONObject }> = []

    client.callTool = async <T extends JSONValue = JSONValue>(
      name: MemoriXToolName,
      arguments_: JSONObject = {},
    ): Promise<T> => {
      calls.push({ name, arguments: arguments_ })
      return { status: "ok" } as unknown as T
    }

    await client.capacityStatus(6_000_000)
    await client.capacityPlan()
    await client.capacityPrune({
      appliedBy: "operator",
      reason: "capacity test",
      maxDeactivations: 5,
    })

    expect(calls).toEqual([
      {
        name: "memorix_capacity_status",
        arguments: { simulate_active_items: 6_000_000 },
      },
      {
        name: "memorix_capacity_plan",
        arguments: {},
      },
      {
        name: "memorix_capacity_prune",
        arguments: {
          applied_by: "operator",
          reason: "capacity test",
          max_deactivations: 5,
        },
      },
    ])
  })

  test("disabled service remains non-blocking", async () => {
    const service = new MemoriXService({
      enabled: false,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "capacity-service"),
    })

    const result = await getCapacityStatus(service, 6_000_000)

    expect(result.metadata.ok).toBe(false)
    expect(result.metadata.failure?.code).toBe("disabled")
  })
})
