import {
  describe,
  expect,
  test,
} from "bun:test"

import {
  memoriXHookOptionsFromEnvironment,
  recordToolResultHook,
  recordUserMessageHook,
  type MemoriXHookService,
} from "../../src/memorix"

function successfulService(
  calls: unknown[],
): MemoriXHookService {
  return {
    recordEvent: async (input) => {
      calls.push(input)

      return {
        ok: true,
        value: {
          short_term_event: {
            event_id: "event_hook",
            content: input.content,
            event_type: input.event_type,
            source: input.source,
            created_at:
              "2026-07-14T10:00:00+00:00",
            project_id: null,
            session_id:
              input.session_id ?? null,
            importance:
              input.importance ?? 0.5,
            confidence:
              input.confidence ?? 1,
            surprise:
              input.surprise ?? 0,
            metadata: {},
          },
          archived_event: {
            event_id: "event_hook",
            content: input.content,
            event_type: input.event_type,
            source: input.source,
            original_created_at:
              "2026-07-14T10:00:00+00:00",
            archived_at:
              "2026-07-14T10:00:01+00:00",
            project_id: null,
            session_id:
              input.session_id ?? null,
            metadata: {},
          },
        },
      }
    },
  }
}

describe("memoriX hook configuration", () => {
  test("all captures are disabled by default", () => {
    const options =
      memoriXHookOptionsFromEnvironment({})

    expect(
      options.captureUserMessages,
    ).toBe(false)

    expect(
      options.captureToolResults,
    ).toBe(false)
  })

  test("parses enabled flags and merges custom exclusions", () => {
    const options =
      memoriXHookOptionsFromEnvironment({
        MEMORIX_HOOK_CAPTURE_MESSAGES:
          "true",
        MEMORIX_HOOK_CAPTURE_TOOL_RESULTS:
          "1",
        MEMORIX_HOOK_IGNORED_TOOLS:
          "memory_store,bash",
      })

    expect(
      options.captureUserMessages,
    ).toBe(true)

    expect(
      options.captureToolResults,
    ).toBe(true)

    expect(options.ignoredTools).toEqual([
      "memory_store",
      "memory_retrieve",
      "memory_candidates_list",
      "memory_candidate_validate",
      "memory_candidate_reject",
      "memory_consolidate",
      "memory_nightly_run",
      "memory_status",
      "project_archive_record",
      "project_archive_list",
      "project_snapshot_rebuild",
      "project_snapshot_get",
      "bash",
    ])
  })

  test("keeps mandatory exclusions when the custom value is empty", () => {
    const options =
      memoriXHookOptionsFromEnvironment({
        MEMORIX_HOOK_IGNORED_TOOLS:
          "   ",
      })

    expect(options.ignoredTools).toEqual([
      "memory_store",
      "memory_retrieve",
      "memory_candidates_list",
      "memory_candidate_validate",
      "memory_candidate_reject",
      "memory_consolidate",
      "memory_nightly_run",
      "memory_status",
      "project_archive_record",
      "project_archive_list",
      "project_snapshot_rebuild",
      "project_snapshot_get",
    ])
  })

  test("normalizes and deduplicates custom exclusions", () => {
    const options =
      memoriXHookOptionsFromEnvironment({
        MEMORIX_HOOK_IGNORED_TOOLS:
          " Bash, bash , MEMORY_STORE, custom_tool ",
      })

    expect(options.ignoredTools).toEqual([
      "memory_store",
      "memory_retrieve",
      "memory_candidates_list",
      "memory_candidate_validate",
      "memory_candidate_reject",
      "memory_consolidate",
      "memory_nightly_run",
      "memory_status",
      "project_archive_record",
      "project_archive_list",
      "project_snapshot_rebuild",
      "project_snapshot_get",
      "bash",
      "custom_tool",
    ])
  })

  test("cannot remove mandatory memory tool exclusions", () => {
    const options =
      memoriXHookOptionsFromEnvironment({
        MEMORIX_HOOK_IGNORED_TOOLS:
          "bash",
      })

    for (const tool of [
      "memory_store",
      "memory_retrieve",
      "memory_candidates_list",
      "memory_candidate_validate",
      "memory_candidate_reject",
      "memory_consolidate",
      "memory_nightly_run",
      "memory_status",
      "project_archive_record",
      "project_archive_list",
      "project_snapshot_rebuild",
      "project_snapshot_get",
    ]) {
      expect(options.ignoredTools).toContain(
        tool,
      )
    }
  })
})

describe("chat.message memoriX hook", () => {
  test("does nothing while disabled", async () => {
    const calls: unknown[] = []
    const service =
      successfulService(calls)

    const result =
      await recordUserMessageHook(
        service,
        memoriXHookOptionsFromEnvironment(
          {},
        ),
        {
          sessionID: "session_test",
          messageID: "message_test",
          agent: "agent_test",
          text: "Hello",
        },
      )

    expect(result.status).toBe("skipped")
    expect(calls).toHaveLength(0)
  })

  test("records one message event", async () => {
    const calls: any[] = []
    const service =
      successfulService(calls)

    const result =
      await recordUserMessageHook(
        service,
        memoriXHookOptionsFromEnvironment({
          MEMORIX_HOOK_CAPTURE_MESSAGES:
            "true",
        }),
        {
          sessionID: "session_test",
          messageID: "message_test",
          agent: "agent_test",
          text: "Remember this discussion.",
        },
      )

    expect(result.status).toBe("recorded")
    expect(calls).toHaveLength(1)
    expect(calls[0].event_type).toBe(
      "opencode_user_message",
    )
    expect(calls[0].source).toBe(
      "opencode.hook.chat.message",
    )
  })

  test("truncates long messages", async () => {
    const calls: any[] = []
    const service =
      successfulService(calls)

    await recordUserMessageHook(
      service,
      memoriXHookOptionsFromEnvironment({
        MEMORIX_HOOK_CAPTURE_MESSAGES:
          "true",
        MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS:
          "5",
      }),
      {
        sessionID: "session_test",
        text: "abcdefghij",
      },
    )

    expect(calls[0].content).toContain(
      "abcde",
    )
    expect(calls[0].content).toContain(
      "truncated",
    )
  })
})

describe("tool.execute.after memoriX hook", () => {
  test("ignores memory tools", async () => {
    const calls: any[] = []
    const service =
      successfulService(calls)

    const result =
      await recordToolResultHook(
        service,
        memoriXHookOptionsFromEnvironment({
          MEMORIX_HOOK_CAPTURE_TOOL_RESULTS:
            "true",
        }),
        {
          sessionID: "session_test",
          callID: "call_test",
          tool: "memory_store",
          args: {},
          title: "Stored",
          output: "Stored memory",
          metadata: {},
        },
      )

    expect(result.status).toBe("skipped")
    expect(calls).toHaveLength(0)
  })

  test("records a normal tool result", async () => {
    const calls: any[] = []
    const service =
      successfulService(calls)

    const result =
      await recordToolResultHook(
        service,
        memoriXHookOptionsFromEnvironment({
          MEMORIX_HOOK_CAPTURE_TOOL_RESULTS:
            "true",
        }),
        {
          sessionID: "session_test",
          callID: "call_test",
          tool: "read",
          args: {
            filePath: "README.md",
          },
          title: "Read README",
          output: "Project documentation",
          metadata: {},
        },
      )

    expect(result.status).toBe("recorded")
    expect(calls).toHaveLength(1)
    expect(calls[0].event_type).toBe(
      "opencode_tool_result",
    )
  })
})
