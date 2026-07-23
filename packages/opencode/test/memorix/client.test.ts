import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXClient,
  MemoriXClientError,
  MemoriXNotConnectedError,
} from "../../src/memorix"

const projectRoot = path.resolve(import.meta.dir, "../../../..")

function createClient() {
  return new MemoriXClient({
    pythonExecutable: process.execPath,
    projectRoot,
    runtimeRoot: path.join(projectRoot, ".tmp", "memorix-client-unit"),
    timeoutMs: 1_000,
  })
}

describe("MemoriXClient local contract", () => {
  test("starts disconnected", () => {
    const client = createClient()

    expect(client.connected).toBe(false)
  })

  test("listTools requires an explicit connection", async () => {
    const client = createClient()

    await expect(client.listTools()).rejects.toBeInstanceOf(
      MemoriXNotConnectedError,
    )
  })

  test("context rejects an empty query before transport use", async () => {
    const client = createClient()

    await expect(client.context("   ")).rejects.toBeInstanceOf(
      MemoriXClientError,
    )
  })

  test("cold search rejects an empty query before transport use", async () => {
    const client = createClient()

    await expect(client.searchColdHistory("")).rejects.toBeInstanceOf(
      MemoriXClientError,
    )
  })

  test("recordEvent rejects empty required values", async () => {
    const client = createClient()

    await expect(
      client.recordEvent({
        content: "",
        event_type: "architecture_rule",
        source: "unit_test",
      }),
    ).rejects.toBeInstanceOf(MemoriXClientError)
  })

  test("close is idempotent while disconnected", async () => {
    const client = createClient()

    await client.close()
    await client.close()

    expect(client.connected).toBe(false)
  })
})
