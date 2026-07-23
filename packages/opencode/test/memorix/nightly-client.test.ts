import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXClient,
  MemoriXService,
  runNightlyThroughMemoriX,
  type JSONObject,
  type JSONValue,
  type MemoriXToolName,
} from "../../src/memorix"

const projectRoot = path.resolve(import.meta.dir, "../../../..")

describe("nightly TypeScript contract", () => {
  test("client calls memorix_run_nightly and forwards the clear flag", async () => {
    const client = new MemoriXClient({
      pythonExecutable: process.execPath,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "memorix-nightly-client"),
    })
    const calls: Array<{ name: MemoriXToolName; arguments: JSONObject }> = []

    client.callTool = async <T extends JSONValue = JSONValue>(
      name: MemoriXToolName,
      arguments_: JSONObject = {},
    ): Promise<T> => {
      calls.push({ name, arguments: arguments_ })
      return { status: "completed" } as unknown as T
    }

    const result = await client.runNightly(false)

    expect(result.status).toBe("completed")
    expect(calls).toEqual([{
      name: "memorix_run_nightly",
      arguments: {
        clear_short_term_after_success: false,
      },
    }])
  })

  test("disabled service remains non-blocking", async () => {
    const service = new MemoriXService({
      enabled: false,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "memorix-nightly-service"),
    })

    const result = await runNightlyThroughMemoriX(service, true)

    expect(result.metadata.ok).toBe(false)
    expect(result.metadata.failure?.code).toBe("disabled")
  })
})
