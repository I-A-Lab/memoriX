import { describe, expect, test } from "bun:test"
import path from "node:path"

import {
  MemoriXClient,
  retrieveMemoryThroughMemoriX,
  storeMemoryThroughMemoriX,
  type JSONObject,
  type JSONValue,
  type MemoryFacadeService,
  type MemoriXContextOptions,
  type MemoriXToolName,
} from "../../src/memorix"

class CapturingClient extends MemoriXClient {
  lastTool?: MemoriXToolName
  lastArguments?: JSONObject

  override async callTool<T extends JSONValue = JSONValue>(
    name: MemoriXToolName,
    args: JSONObject = {},
  ): Promise<T> {
    this.lastTool = name
    this.lastArguments = args

    return {
      query: String(args.query ?? ""),
      source: "hot_site",
      matches: [],
    } as unknown as T
  }
}

describe("explicit scoped memory transport", () => {
  test("client maps scope to the Python MCP argument names", async () => {
    const projectRoot = path.resolve(import.meta.dir, "../../../..")
    const client = new CapturingClient({
      pythonExecutable: process.execPath,
      projectRoot,
      runtimeRoot: path.join(projectRoot, ".tmp", "memorix-scope-client"),
    })

    await client.context("delimiter", {
      projectID: "project-alpha",
      userID: "user-elwen",
      topK: 3,
    })

    expect(client.lastTool).toBe("memorix_context")
    expect(client.lastArguments).toEqual({
      query: "delimiter",
      top_k: 3,
      project_id: "project-alpha",
      user_id: "user-elwen",
    })
  })

  test("retrieval facade forwards project and user filters", async () => {
    let received: MemoriXContextOptions | undefined

    const service = {
      context: async (
        query: string,
        options?: MemoriXContextOptions,
      ) => {
        received = options
        return {
          ok: true as const,
          value: {
            query,
            source: "hot_site" as const,
            matches: [],
          },
        }
      },
    } as unknown as MemoryFacadeService

    await retrieveMemoryThroughMemoriX(service, {
      query: "delimiter",
      projectID: "project-alpha",
      userID: "user-elwen",
    })

    expect(received?.projectID).toBe("project-alpha")
    expect(received?.userID).toBe("user-elwen")
  })

  test("storage facade attaches explicit scope", async () => {
    let recordedProject: string | null | undefined
    let recordedUser: unknown
    let candidateProject: unknown
    let candidateUser: unknown

    const service = {
      recordEvent: async (input) => {
        recordedProject = input.project_id
        recordedUser = input.metadata?.user_id
        return {
          ok: true as const,
          value: {
            short_term_event: {
              event_id: "event-scope",
              content: input.content,
              event_type: input.event_type,
              source: input.source,
              created_at: "2026-07-27T00:00:00+00:00",
              project_id: input.project_id ?? null,
              session_id: input.session_id ?? null,
              importance: input.importance ?? 0.9,
              confidence: input.confidence ?? 1,
              surprise: input.surprise ?? 0.5,
              metadata: input.metadata ?? {},
            },
            archived_event: {
              event_id: "event-scope",
              content: input.content,
              event_type: input.event_type,
              source: input.source,
              original_created_at: "2026-07-27T00:00:00+00:00",
              archived_at: "2026-07-27T00:00:01+00:00",
              project_id: input.project_id ?? null,
              session_id: input.session_id ?? null,
              metadata: input.metadata ?? {},
            },
          },
        }
      },
      proposeCandidate: async (input) => {
        candidateProject = input.metadata?.project_id
        candidateUser = input.metadata?.user_id
        return {
          ok: true as const,
          value: {
            candidate_id: "candidate-scope",
            content: input.content,
            reason: input.reason,
            source_event_ids: input.source_event_ids,
            created_at: "2026-07-27T00:00:02+00:00",
            status: "pending" as const,
            importance: input.importance ?? 0.9,
            confidence: input.confidence ?? 1,
            surprise: input.surprise ?? 0.5,
            target_memory_id: input.target_memory_id ?? null,
            metadata: input.metadata ?? {},
          },
        }
      },
      context: async () => ({
        ok: true as const,
        value: {
          query: "",
          source: "hot_site" as const,
          matches: [],
        },
      }),
    } as MemoryFacadeService

    await storeMemoryThroughMemoriX(
      service,
      {
        subject: "CSV delimiter",
        content: "Use semicolon",
        tags: ["csv"],
      },
      {
        sessionID: "session",
        messageID: "message",
        agent: "agent",
        projectID: "project-alpha",
        userID: "user-elwen",
      },
    )

    expect(recordedProject).toBe("project-alpha")
    expect(recordedUser).toBe("user-elwen")
    expect(candidateProject).toBe("project-alpha")
    expect(candidateUser).toBe("user-elwen")
  })
})
