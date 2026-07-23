import { describe, expect, test } from "bun:test"
import path from "node:path"
import {
  MemoriXClient,
  type JSONObject,
  type JSONValue,
  type MemoriXToolName,
} from "../../src/memorix"

const projectRoot = path.resolve(
  import.meta.dir,
  "../../../..",
)

describe("retention ranking TypeScript contract", () => {
  test("client forwards read-only retention operations", async () => {
    const client = new MemoriXClient({
      pythonExecutable: process.execPath,
      projectRoot,
      runtimeRoot: path.join(
        projectRoot,
        ".tmp",
        "retention-ranking-client",
      ),
    })

    const calls: Array<{
      name: MemoriXToolName
      arguments: JSONObject
    }> = []

    client.callTool = async <
      T extends JSONValue = JSONValue,
    >(
      name: MemoriXToolName,
      arguments_: JSONObject = {},
    ): Promise<T> => {
      calls.push({
        name,
        arguments: arguments_,
      })

      return {
        status: "ok",
      } as unknown as T
    }

    await client.retentionRankingStatus(
      6_000_000,
      1,
    )

    await client.retentionRankingInspect(
      "memory-1",
    )

    expect(calls).toEqual([
      {
        name: "memorix_retention_ranking_status",
        arguments: {
          simulate_count: 6_000_000,
          assessment_limit: 1,
        },
      },
      {
        name: "memorix_retention_ranking_inspect",
        arguments: {
          memory_id: "memory-1",
        },
      },
    ])
  })
})
