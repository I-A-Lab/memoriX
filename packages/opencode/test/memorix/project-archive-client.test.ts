import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXClient,
  MemoriXClientError,
  MemoriXService,
} from "../../src/memorix"

const projectRoot = path.resolve(import.meta.dir, "../../../..")

function client() {
  return new MemoriXClient({
    pythonExecutable: process.execPath,
    projectRoot,
    runtimeRoot: path.join(projectRoot, ".tmp", "memorix-project-client"),
  })
}

describe("project archive TypeScript contract", () => {
  test("client rejects an empty project ID before transport use", async () => {
    await expect(
      client().rebuildProjectSnapshot("   "),
    ).rejects.toBeInstanceOf(MemoriXClientError)
  })

  test("client rejects missing source events", async () => {
    await expect(
      client().recordProjectArchiveEntry({
        project_id: "memorix",
        entry_type: "decision",
        title: "Decision",
        content: "Keep the archive append-only.",
        source_event_ids: [],
        author: "Elwen",
      }),
    ).rejects.toBeInstanceOf(MemoriXClientError)
  })

  test("disabled service returns a safe failure", async () => {
    const service = new MemoriXService({
      enabled: false,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "memorix-project-service"),
    })

    const result = await service.getProjectSnapshot("memorix")
    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.code).toBe("disabled")
  })
})
