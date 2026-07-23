import {
  describe,
  expect,
  test,
} from "bun:test"

import {
  retrieveMemoryThroughMemoriX,
  storeMemoryThroughMemoriX,
  type MemoryFacadeService,
} from "../../src/memorix"

const context = {
  sessionID: "session_test",
  messageID: "message_test",
  agent: "test_agent",
}

function createService(
  overrides: Partial<MemoryFacadeService> = {},
): MemoryFacadeService {
  return {
    recordEvent: async () => ({
      ok: true,
      value: {
        short_term_event: {
          event_id: "event_test",
          content: "canonical",
          event_type:
            "opencode_memory_fact",
          source:
            "opencode.memory_store",
          created_at:
            "2026-07-14T10:00:00+00:00",
          project_id: null,
          session_id: "session_test",
          importance: 0.9,
          confidence: 1,
          surprise: 0.5,
          metadata: {},
        },
        archived_event: {
          event_id: "event_test",
          content: "canonical",
          event_type:
            "opencode_memory_fact",
          source:
            "opencode.memory_store",
          original_created_at:
            "2026-07-14T10:00:00+00:00",
          archived_at:
            "2026-07-14T10:00:01+00:00",
          project_id: null,
          session_id: "session_test",
          metadata: {},
        },
      },
    }),
    proposeCandidate: async () => ({
      ok: true,
      value: {
        candidate_id:
          "candidate_test",
        content: "canonical",
        reason: "test",
        source_event_ids: [
          "event_test",
        ],
        created_at:
          "2026-07-14T10:00:02+00:00",
        status: "pending",
        importance: 0.9,
        confidence: 1,
        surprise: 0.5,
        target_memory_id: null,
        metadata: {},
      },
    }),
    context: async (query) => ({
      ok: true,
      value: {
        query,
        source: "hot_site",
        matches: [],
      },
    }),
    ...overrides,
  }
}

describe("memory_store memoriX facade", () => {
  test("archives and creates a pending candidate", async () => {
    const service = createService()

    const result =
      await storeMemoryThroughMemoriX(
        service,
        {
          subject: "Retrieval contract",
          content:
            "Retrieval is hot-site only.",
          tags: ["architecture", "hot"],
        },
        context,
      )

    expect(result.metadata.status).toBe(
      "pending_review",
    )
    expect(result.metadata.eventID).toBe(
      "event_test",
    )
    expect(result.metadata.candidateID).toBe(
      "candidate_test",
    )
    expect(result.output).toContain(
      "human validates it",
    )
  })

  test("does not propose when recording fails", async () => {
    let proposeCalls = 0

    const service = createService({
      recordEvent: async () => ({
        ok: false,
        code: "disabled",
        message: "memoriX is disabled.",
      }),
      proposeCandidate: async () => {
        proposeCalls += 1
        throw new Error(
          "should not be called",
        )
      },
    })

    const result =
      await storeMemoryThroughMemoriX(
        service,
        {
          subject: "Fact",
          content: "Content",
          tags: [],
        },
        context,
      )

    expect(result.metadata.status).toBe(
      "unavailable",
    )
    expect(proposeCalls).toBe(0)
  })

  test("reports archived-only partial success", async () => {
    const service = createService({
      proposeCandidate: async () => ({
        ok: false,
        code: "operation",
        message:
          "candidate service failed",
      }),
    })

    const result =
      await storeMemoryThroughMemoriX(
        service,
        {
          subject: "Fact",
          content: "Content",
          tags: [],
        },
        context,
      )

    expect(result.metadata.status).toBe(
      "archived_only",
    )
    expect(result.metadata.eventID).toBe(
      "event_test",
    )
    expect(result.metadata.candidateID)
      .toBeUndefined()
  })
})

describe("memory_retrieve memoriX facade", () => {
  test("returns validated hot-site facts", async () => {
    const service = createService({
      context: async (query) => ({
        ok: true,
        value: {
          query,
          source: "hot_site",
          matches: [
            {
              memory_id:
                "memory_test",
              content:
                "Subject: Retrieval contract",
              score: 0.98,
              metadata: {
                subject:
                  "Retrieval contract",
                original_content:
                  "Retrieval is hot-only.",
                tags: [
                  "architecture",
                  "hot",
                ],
                validated_at:
                  "2026-07-14T11:00:00+00:00",
              },
            },
          ],
        },
      }),
    })

    const result =
      await retrieveMemoryThroughMemoriX(
        service,
        {
          query: "retrieval",
          tags: ["hot"],
        },
      )

    expect(result.metadata.source).toBe(
      "hot_site",
    )
    expect(result.metadata.results).toHaveLength(
      1,
    )
    expect(
      result.metadata.results[0]?.id,
    ).toBe("memory_test")
    expect(
      result.metadata.results[0]?.content,
    ).toBe("Retrieval is hot-only.")
  })

  test("never accepts a cold-audit source", async () => {
    const service = createService({
      context: async (query) => ({
        ok: true,
        value: {
          query,
          source: "cold_audit",
          matches: [],
        },
      }),
    })

    const result =
      await retrieveMemoryThroughMemoriX(
        service,
        {
          query: "historical",
        },
      )

    expect(
      result.metadata.results,
    ).toHaveLength(0)
    expect(
      result.metadata.failure?.code,
    ).toBe("contract_violation")
  })

  test("returns a safe result when disabled", async () => {
    const service = createService({
      context: async () => ({
        ok: false,
        code: "disabled",
        message: "memoriX is disabled.",
      }),
    })

    const result =
      await retrieveMemoryThroughMemoriX(
        service,
        {
          query: "anything",
        },
      )

    expect(
      result.metadata.results,
    ).toHaveLength(0)
    expect(
      result.metadata.failure?.code,
    ).toBe("disabled")
  })
})
