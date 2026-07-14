import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXService,
  memoriXServiceOptionsFromEnvironment,
  type JSONObject,
  type JSONValue,
  type MemoriXClientContract,
  type MemoriXRetrievalResult,
  type MemoriXStatus,
  type MemoriXToolName,
} from "../../src/memorix"

const projectRoot = path.resolve(
  import.meta.dir,
  "../../../..",
)

class FakeClient implements MemoriXClientContract {
  connected = false
  connectCalls = 0
  closeCalls = 0
  statusCalls = 0
  contextCalls = 0
  recordCalls = 0
  failConnect = false
  failStatus = false

  async connect(): Promise<void> {
    this.connectCalls += 1

    if (this.failConnect) {
      throw new Error("fake connect failure")
    }

    this.connected = true
  }

  async status(): Promise<MemoriXStatus> {
    this.statusCalls += 1

    if (this.failStatus) {
      throw new Error("fake status failure")
    }

    return {
      architecture: "memorix_hot_cold",
      retrieval_contract:
        "hot_site_only_no_cold_fallback",
      cold_site_contract:
        "explicit_audit_history_only",
      automatic_rehydration: false,
      short_term_events: 0,
      cold_archive_events: 0,
      hot_memories_total: 0,
      hot_memories_active: 0,
      candidates: {
        pending: 0,
        validated: 0,
        rejected: 0,
      },
      paths: {},
      titan: {},
    }
  }

  async context(): Promise<MemoriXRetrievalResult> {
    this.contextCalls += 1

    return {
      query: "test",
      source: "hot_site",
      matches: [],
    }
  }

  async searchColdHistory(): Promise<MemoriXRetrievalResult> {
    return {
      query: "test",
      source: "cold_audit",
      matches: [],
    }
  }

  async recordEvent() {
    this.recordCalls += 1

    return {
      short_term_event: {
        event_id: "event_fake",
        content: "fake",
        event_type: "test",
        source: "unit_test",
        created_at:
          "2026-07-14T10:00:00+00:00",
        project_id: null,
        session_id: null,
        importance: 0.5,
        confidence: 1,
        surprise: 0,
        metadata: {},
      },
      archived_event: {
        event_id: "event_fake",
        content: "fake",
        event_type: "test",
        source: "unit_test",
        original_created_at:
          "2026-07-14T10:00:00+00:00",
        archived_at:
          "2026-07-14T10:00:01+00:00",
        project_id: null,
        session_id: null,
        metadata: {},
      },
    }
  }

  async proposeCandidate() {
    return {
      candidate_id: "candidate_fake",
      content: "fake",
      reason: "test",
      source_event_ids: ["event_fake"],
      created_at:
        "2026-07-14T10:00:02+00:00",
      status: "pending" as const,
      importance: 0.5,
      confidence: 1,
      surprise: 0,
      target_memory_id: null,
      metadata: {},
    }
  }

  async callTool<T extends JSONValue = JSONValue>(
    _name: MemoriXToolName,
    _arguments: JSONObject = {},
  ): Promise<T> {
    return {} as T
  }

  async close(): Promise<void> {
    this.closeCalls += 1
    this.connected = false
  }
}

function serviceWithFake(
  fake: FakeClient,
  enabled = true,
): MemoriXService {
  return new MemoriXService(
    {
      enabled,
      pythonExecutable:
        "C:\\fake-python\\python.exe",
      projectRoot,
      runtimeRoot: path.join(
        projectRoot,
        ".tmp",
        "memorix-service-test",
      ),
    },
    {
      clientFactory: () => fake,
    },
  )
}

describe("memoriX service environment", () => {
  test("is disabled by default", () => {
    const options =
      memoriXServiceOptionsFromEnvironment(
        {},
        {
          projectRoot,
          runtimeRoot: path.join(
            projectRoot,
            ".tmp",
            "memorix-env-test",
          ),
        },
      )

    expect(options.enabled).toBe(false)
  })

  test("parses enabled environment values", () => {
    const options =
      memoriXServiceOptionsFromEnvironment(
        {
          MEMORIX_ENABLED: "true",
          MEMORIX_PYTHON_EXECUTABLE:
            "C:\\Python\\python.exe",
          MEMORIX_TIMEOUT_MS: "30000",
          MEMORIX_TITAN_D_MODEL: "32",
          MEMORIX_TITAN_MIN_SCORE: "0",
        },
        {
          projectRoot,
          runtimeRoot: path.join(
            projectRoot,
            ".tmp",
            "memorix-env-test",
          ),
        },
      )

    expect(options.enabled).toBe(true)
    expect(options.timeoutMs).toBe(30_000)
    expect(options.titanDModel).toBe(32)
    expect(options.titanMinScore).toBe(0)
  })
})

describe("MemoriXService lazy lifecycle", () => {
  test("does not create or connect a client in constructor", () => {
    const fake = new FakeClient()
    let factoryCalls = 0

    const service = new MemoriXService(
      {
        enabled: true,
        pythonExecutable:
          "C:\\fake-python\\python.exe",
        projectRoot,
        runtimeRoot: path.join(
          projectRoot,
          ".tmp",
          "memorix-lazy-test",
        ),
      },
      {
        clientFactory: () => {
          factoryCalls += 1
          return fake
        },
      },
    )

    expect(factoryCalls).toBe(0)
    expect(fake.connectCalls).toBe(0)
    expect(service.connected).toBe(false)
  })

  test("connects once on first operation", async () => {
    const fake = new FakeClient()
    const service = serviceWithFake(fake)

    const first = await service.status()
    const second = await service.status()

    expect(first.ok).toBe(true)
    expect(second.ok).toBe(true)
    expect(fake.connectCalls).toBe(1)
    expect(fake.statusCalls).toBe(2)
    expect(service.connected).toBe(true)

    await service.close()
  })

  test("shares one concurrent connection", async () => {
    const fake = new FakeClient()
    const service = serviceWithFake(fake)

    const results = await Promise.all([
      service.status(),
      service.context("test"),
      service.recordEvent({
        content: "event",
        event_type: "test",
        source: "unit_test",
      }),
    ])

    expect(results.every((result) => result.ok)).toBe(true)
    expect(fake.connectCalls).toBe(1)

    await service.close()
  })

  test("close is idempotent", async () => {
    const fake = new FakeClient()
    const service = serviceWithFake(fake)

    await service.status()
    await service.close()
    await service.close()

    expect(fake.closeCalls).toBe(1)
    expect(service.connected).toBe(false)
  })
})

describe("MemoriXService non-blocking failures", () => {
  test("disabled service returns a safe failure", async () => {
    const fake = new FakeClient()
    const service = serviceWithFake(fake, false)

    const result = await service.status()

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.code).toBe("disabled")
    }

    expect(fake.connectCalls).toBe(0)
  })

  test("missing Python configuration returns a safe failure", async () => {
    const service = new MemoriXService({
      enabled: true,
      projectRoot,
      runtimeRoot: path.join(
        projectRoot,
        ".tmp",
        "memorix-config-test",
      ),
    })

    const result = await service.connect()

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.code).toBe("configuration")
    }
  })

  test("connection error is captured", async () => {
    const fake = new FakeClient()
    fake.failConnect = true

    const service = serviceWithFake(fake)
    const result = await service.connect()

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.code).toBe("connection")
      expect(result.message).toContain(
        "fake connect failure",
      )
    }
  })

  test("operation error is captured", async () => {
    const fake = new FakeClient()
    fake.failStatus = true

    const service = serviceWithFake(fake)
    const result = await service.status()

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.code).toBe("operation")
      expect(result.message).toContain(
        "fake status failure",
      )
    }

    await service.close()
  })
})
