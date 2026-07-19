import path from "node:path"
import { access } from "node:fs/promises"

import { Client } from "@modelcontextprotocol/sdk/client/index.js"
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js"

import {
  MemoriXClientError,
  MemoriXNotConnectedError,
  MemoriXTimeoutError,
  MemoriXToolCallError,
} from "./errors"
import type {
  JSONObject,
  JSONValue,
  MemoriXCandidate,
  MemoriXClientOptions,
  MemoriXProposeCandidateInput,
  MemoriXProjectArchiveEntry,
  MemoriXProjectArchiveEntryType,
  MemoriXProjectEntryRecordInput,
  MemoriXProjectSnapshot,
  MemoriXRecordedEvent,
  MemoriXRecordEventInput,
  MemoriXRetrievalResult,
  MemoriXStatus,
  MemoriXToolCallResult,
  MemoriXToolDefinition,
  MemoriXToolName,
} from "./types"

const CLIENT_NAME = "opencode-memorix"
const CLIENT_VERSION = "0.1.0"
const DEFAULT_TIMEOUT_MS = 15_000

function withTimeout<T>(
  operation: string,
  promise: Promise<T>,
  timeoutMs: number,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined

  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new MemoriXTimeoutError(operation, timeoutMs))
    }, timeoutMs)
  })

  return Promise.race([promise, timeout]).finally(() => {
    if (timer) clearTimeout(timer)
  })
}

function asRecord(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new MemoriXClientError("memoriX returned an invalid object payload.")
  }

  return value as Record<string, unknown>
}

export class MemoriXClient {
  readonly options: Required<
    Pick<
      MemoriXClientOptions,
      | "timeoutMs"
      | "titanDModel"
      | "titanHiddenDim"
      | "titanMaxItems"
      | "titanDevice"
      | "titanTopK"
      | "titanMinScore"
    >
  > &
    Omit<
      MemoriXClientOptions,
      | "timeoutMs"
      | "titanDModel"
      | "titanHiddenDim"
      | "titanMaxItems"
      | "titanDevice"
      | "titanTopK"
      | "titanMinScore"
    >

  private client?: Client
  private transport?: StdioClientTransport
  private connecting?: Promise<void>
  private closing?: Promise<void>

  constructor(options: MemoriXClientOptions) {
    this.options = {
      ...options,
      timeoutMs: options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
      titanDModel: options.titanDModel ?? 256,
      titanHiddenDim: options.titanHiddenDim ?? 256,
      titanMaxItems: options.titanMaxItems ?? 50_000,
      titanDevice: options.titanDevice ?? "cpu",
      titanTopK: options.titanTopK ?? 5,
      titanMinScore: options.titanMinScore ?? 0.12,
    }
  }

  get connected(): boolean {
    return this.client !== undefined && this.transport !== undefined
  }

  async connect(): Promise<void> {
    if (this.connected) return

    if (this.connecting) {
      await this.connecting
      return
    }

    this.connecting = this.connectInternal()

    try {
      await this.connecting
    } finally {
      this.connecting = undefined
    }
  }

  private async connectInternal(): Promise<void> {
    const pythonExecutable = path.resolve(this.options.pythonExecutable)
    const projectRoot = path.resolve(this.options.projectRoot)
    const runtimeRoot = path.resolve(this.options.runtimeRoot)
    const launcher = path.join(projectRoot, "scripts", "memorix_mcp_server.py")

    await access(pythonExecutable).catch((cause) => {
      throw new MemoriXClientError(
        `Python executable not found: ${pythonExecutable}`,
        { cause },
      )
    })

    await access(launcher).catch((cause) => {
      throw new MemoriXClientError(
        `memoriX MCP launcher not found: ${launcher}`,
        { cause },
      )
    })

    const client = new Client(
      {
        name: CLIENT_NAME,
        version: CLIENT_VERSION,
      },
      {
        capabilities: {},
      },
    )

    const transport = new StdioClientTransport({
      command: pythonExecutable,
      args: [launcher],
      cwd: projectRoot,
      stderr: "inherit",
      env: {
        ...process.env,
        MEMORIX_RUNTIME_ROOT: runtimeRoot,
        MEMORIX_TITAN_D_MODEL: String(this.options.titanDModel),
        MEMORIX_TITAN_HIDDEN_DIM: String(this.options.titanHiddenDim),
        MEMORIX_TITAN_MAX_ITEMS: String(this.options.titanMaxItems),
        MEMORIX_TITAN_DEVICE: this.options.titanDevice,
        MEMORIX_TITAN_TOP_K: String(this.options.titanTopK),
        MEMORIX_TITAN_MIN_SCORE: String(this.options.titanMinScore),
      },
    })

    try {
      await withTimeout(
        "connect",
        client.connect(transport),
        this.options.timeoutMs,
      )
    } catch (cause) {
      await client.close().catch(() => undefined)

      if (cause instanceof MemoriXClientError) throw cause

      throw new MemoriXClientError(
        "Unable to connect to the memoriX MCP server.",
        { cause },
      )
    }

    this.client = client
    this.transport = transport
  }

  async listTools(): Promise<MemoriXToolDefinition[]> {
    const client = this.requireClient()

    const result = await withTimeout(
      "tools/list",
      client.listTools(),
      this.options.timeoutMs,
    )

    return result.tools as MemoriXToolDefinition[]
  }

  async callTool<T extends JSONValue = JSONValue>(
    name: MemoriXToolName,
    arguments_: JSONObject = {},
  ): Promise<T> {
    const client = this.requireClient()

    const rawResult = await withTimeout(
      `tools/call:${name}`,
      client.callTool({
        name,
        arguments: arguments_,
      }),
      this.options.timeoutMs,
    )

    const result = rawResult as MemoriXToolCallResult

    if (result.isError) {
      const message =
        result.content
          ?.map((item) => item.text)
          .filter((item): item is string => typeof item === "string")
          .join("\n") || "Unknown memoriX tool error."

      throw new MemoriXToolCallError(name, message)
    }

    if (result.structuredContent === undefined) {
      throw new MemoriXToolCallError(
        name,
        "The server returned no structuredContent.",
      )
    }

    const structured = result.structuredContent
    const keys = Object.keys(structured)

    if (
      keys.length === 1 &&
      keys[0] === "value"
    ) {
      return structured.value as T
    }

    return structured as T
  }

  async status(): Promise<MemoriXStatus> {
    const value = await this.callTool("memorix_status")
    return asRecord(value) as unknown as MemoriXStatus
  }

  async context(
    query: string,
    options?: {
      role?: string
      topK?: number
    },
  ): Promise<MemoriXRetrievalResult> {
    if (!query.trim()) {
      throw new MemoriXClientError("memoriX context query must not be empty.")
    }

    const value = await this.callTool("memorix_context", {
      query,
      ...(options?.role ? { role: options.role } : {}),
      ...(options?.topK !== undefined ? { top_k: options.topK } : {}),
    })

    return asRecord(value) as unknown as MemoriXRetrievalResult
  }

  async searchColdHistory(
    query: string,
    options?: {
      limit?: number
    },
  ): Promise<MemoriXRetrievalResult> {
    if (!query.trim()) {
      throw new MemoriXClientError("Cold-history query must not be empty.")
    }

    const value = await this.callTool("memorix_search_cold_history", {
      query,
      ...(options?.limit !== undefined ? { limit: options.limit } : {}),
    })

    return asRecord(value) as unknown as MemoriXRetrievalResult
  }

  async recordEvent(
    input: MemoriXRecordEventInput,
  ): Promise<MemoriXRecordedEvent> {
    if (!input.content.trim()) {
      throw new MemoriXClientError("Event content must not be empty.")
    }

    if (!input.event_type.trim()) {
      throw new MemoriXClientError("Event type must not be empty.")
    }

    if (!input.source.trim()) {
      throw new MemoriXClientError("Event source must not be empty.")
    }

    const value = await this.callTool(
      "memorix_record_event",
      input as unknown as JSONObject,
    )

    return asRecord(value) as unknown as MemoriXRecordedEvent
  }

  async proposeCandidate(
    input: MemoriXProposeCandidateInput,
  ): Promise<MemoriXCandidate> {
    if (!input.content.trim()) {
      throw new MemoriXClientError(
        "Candidate content must not be empty.",
      )
    }

    if (!input.reason.trim()) {
      throw new MemoriXClientError(
        "Candidate reason must not be empty.",
      )
    }

    if (
      input.source_event_ids.length === 0 ||
      input.source_event_ids.some(
        (eventID) => !eventID.trim(),
      )
    ) {
      throw new MemoriXClientError(
        "Candidate source_event_ids must contain non-empty event IDs.",
      )
    }

    const value = await this.callTool(
      "memorix_propose_candidate",
      input as unknown as JSONObject,
    )

    return asRecord(value) as unknown as MemoriXCandidate
  }

  async runNightly(
    clearShortTermAfterSuccess = true,
  ): Promise<JSONObject> {
    return this.callTool<JSONObject>(
      "memorix_run_nightly",
      {
        clear_short_term_after_success:
          clearShortTermAfterSuccess,
      },
    )
  }


  async capacityStatus(simulateActiveItems?: number): Promise<JSONObject> {
    return this.callTool<JSONObject>("memorix_capacity_status", {
      simulate_active_items: simulateActiveItems ?? null,
    })
  }

  async capacityPlan(): Promise<JSONObject> {
    return this.callTool<JSONObject>("memorix_capacity_plan")
  }

  async capacityPrune(input: { appliedBy: string; reason: string; maxDeactivations?: number }): Promise<JSONObject> {
    return this.callTool<JSONObject>("memorix_capacity_prune", {
      applied_by: input.appliedBy, reason: input.reason,
      max_deactivations: input.maxDeactivations ?? null,
    })
  }

  async memoryPressureStatus(
    simulateCount?: number,
    assessmentLimit = 100,
  ): Promise<JSONObject> {
    return this.callTool<JSONObject>(
      "memorix_memory_pressure_status",
      {
        simulate_count: simulateCount ?? null,
        assessment_limit: assessmentLimit,
      },
    )
  }

  async memoryPressureInspect(
    memoryID: string,
  ): Promise<JSONObject | null> {
    if (!memoryID.trim()) {
      throw new MemoriXClientError(
        "Memory ID must not be empty.",
      )
    }

    return this.callTool<JSONObject | null>(
      "memorix_memory_pressure_inspect",
      { memory_id: memoryID.trim() },
    )
  }

  async retentionRankingStatus(
    simulateCount?: number,
    assessmentLimit = 100,
  ): Promise<JSONObject> {
    return this.callTool<JSONObject>(
      "memorix_retention_ranking_status",
      {
        simulate_count: simulateCount ?? null,
        assessment_limit: assessmentLimit,
      },
    )
  }

  async retentionRankingInspect(
    memoryID: string,
  ): Promise<JSONObject | null> {
    if (!memoryID.trim()) {
      throw new MemoriXClientError(
        "Memory ID must not be empty.",
      )
    }

    return this.callTool<JSONObject | null>(
      "memorix_retention_ranking_inspect",
      { memory_id: memoryID.trim() },
    )
  }

  async adaptiveRoutingPlan(
    input: JSONObject,
  ): Promise<JSONObject> {
    return this.callTool<JSONObject>(
      "memorix_adaptive_routing_plan",
      input,
    )
  }

  async recordProjectArchiveEntry(
    input: MemoriXProjectEntryRecordInput,
  ): Promise<MemoriXProjectArchiveEntry> {
    if (!input.project_id.trim()) {
      throw new MemoriXClientError("Project ID must not be empty.")
    }
    if (!input.title.trim() || !input.content.trim() || !input.author.trim()) {
      throw new MemoriXClientError("Project archive text fields must not be empty.")
    }
    if (
      input.source_event_ids.length === 0 ||
      input.source_event_ids.some((value) => !value.trim())
    ) {
      throw new MemoriXClientError(
        "Project archive source_event_ids must contain non-empty IDs.",
      )
    }

    const value = await this.callTool(
      "memorix_project_entry_record",
      input as unknown as JSONObject,
    )
    return asRecord(value) as unknown as MemoriXProjectArchiveEntry
  }

  async listProjectArchiveEntries(options: {
    projectID?: string | null
    entryType?: MemoriXProjectArchiveEntryType | null
  } = {}): Promise<MemoriXProjectArchiveEntry[]> {
    return this.callTool<MemoriXProjectArchiveEntry[]>(
      "memorix_project_entries_list",
      {
        ...(options.projectID !== undefined
          ? { project_id: options.projectID }
          : {}),
        ...(options.entryType !== undefined
          ? { entry_type: options.entryType }
          : {}),
      },
    )
  }

  async rebuildProjectSnapshot(
    projectID: string,
  ): Promise<MemoriXProjectSnapshot> {
    if (!projectID.trim()) {
      throw new MemoriXClientError("Project ID must not be empty.")
    }
    const value = await this.callTool(
      "memorix_project_snapshot_rebuild",
      { project_id: projectID },
    )
    return asRecord(value) as unknown as MemoriXProjectSnapshot
  }

  async getProjectSnapshot(
    projectID: string,
  ): Promise<MemoriXProjectSnapshot | null> {
    if (!projectID.trim()) {
      throw new MemoriXClientError("Project ID must not be empty.")
    }
    return this.callTool<MemoriXProjectSnapshot | null>(
      "memorix_project_snapshot_get",
      { project_id: projectID },
    )
  }

  async close(): Promise<void> {
    if (this.closing) {
      await this.closing
      return
    }

    if (!this.client) {
      this.transport = undefined
      return
    }

    this.closing = this.closeInternal()

    try {
      await this.closing
    } finally {
      this.closing = undefined
    }
  }

  private async closeInternal(): Promise<void> {
    const client = this.client

    if (!client) {
      this.transport = undefined
      return
    }

    this.client = undefined
    this.transport = undefined

    await withTimeout(
      "close",
      client.close(),
      this.options.timeoutMs,
    ).catch((cause) => {
      if (cause instanceof MemoriXTimeoutError) throw cause

      throw new MemoriXClientError(
        "Unable to close the memoriX MCP client.",
        { cause },
      )
    })
  }

  private requireClient(): Client {
    if (!this.client) {
      throw new MemoriXNotConnectedError()
    }

    return this.client
  }

  async [Symbol.asyncDispose](): Promise<void> {
    await this.close()
  }
}
