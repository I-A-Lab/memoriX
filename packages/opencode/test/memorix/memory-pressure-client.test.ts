import { describe, expect, test } from "bun:test"
import path from "node:path"
import {
  MemoriXClient,
  MemoriXService,
  getMemoryPressureStatus,
  type JSONObject,
  type JSONValue,
  type MemoriXToolName,
} from "../../src/memorix"
const projectRoot = path.resolve(import.meta.dir, "../../../..")

describe("memory pressure TypeScript contract", () => {
  test("client forwards read-only pressure operations", async () => {
    const client = new MemoriXClient({ pythonExecutable: process.execPath, projectRoot, runtimeRoot: path.join(projectRoot, ".tmp", "pressure-client") })
    const calls: Array<{ name: MemoriXToolName; arguments: JSONObject }> = []
    client.callTool = async <T extends JSONValue = JSONValue>(name: MemoriXToolName, arguments_: JSONObject = {}): Promise<T> => {
      calls.push({ name, arguments: arguments_ }); return { status: "ok" } as unknown as T
    }
    await client.memoryPressureStatus(6_000_000, 1)
    await client.memoryPressureInspect("memory-1")
    expect(calls).toEqual([
      { name: "memorix_memory_pressure_status", arguments: { simulate_count: 6_000_000, assessment_limit: 1 } },
      { name: "memorix_memory_pressure_inspect", arguments: { memory_id: "memory-1" } },
    ])
  })
  test("disabled service remains non-blocking", async () => {
    const service = new MemoriXService({ enabled: false, projectRoot, runtimeRoot: path.join(projectRoot, ".tmp", "pressure-service") })
    const result = await getMemoryPressureStatus(service)
    expect(result.metadata.ok).toBe(false)
    expect(result.metadata.failure?.code).toBe("disabled")
  })
})
