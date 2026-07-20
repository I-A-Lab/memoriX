import path from "node:path"
import os from "node:os"

import { MemoriXClient } from "./client"
import {
  MemoriXClientError,
  MemoriXConfigurationError,
  MemoriXDisabledError,
} from "./errors"
import type {
  MemoriXCandidate,
  MemoriXProposeCandidateInput,
  MemoriXProjectArchiveEntry,
  MemoriXProjectArchiveEntryType,
  MemoriXProjectEntryRecordInput,
  MemoriXProjectSnapshot,
  MemoriXRecordedEvent,
  MemoriXRecordEventInput,
  MemoriXRetrievalResult,
  MemoriXServiceEnvironment,
  MemoriXServiceFailure,
  MemoriXServiceOptions,
  MemoriXServiceResult,
  MemoriXStatus,
  JSONObject,
  MemoriXCandidateStatus,
} from "./types"

export type MemoriXClientContract = Pick<
  MemoriXClient,
  | "connected"
  | "connect"
  | "status"
  | "context"
  | "searchColdHistory"
  | "recordEvent"
  | "proposeCandidate"
  | "callTool"
  | "close"
>

export type MemoriXClientFactory = (
  options: ConstructorParameters<typeof MemoriXClient>[0],
) => MemoriXClientContract

export type MemoriXServiceDependencies = {
  clientFactory?: MemoriXClientFactory
}

const DEFAULT_TIMEOUT_MS = 15_000

function parseBoolean(
  value: string | undefined,
  fallback: boolean,
): boolean {
  if (value === undefined) return fallback

  const normalized = value.trim().toLowerCase()

  if (
    normalized === "1" ||
    normalized === "true" ||
    normalized === "yes" ||
    normalized === "on"
  ) {
    return true
  }

  if (
    normalized === "0" ||
    normalized === "false" ||
    normalized === "no" ||
    normalized === "off"
  ) {
    return false
  }

  return fallback
}

function parsePositiveInteger(
  value: string | undefined,
  fallback: number,
): number {
  if (value === undefined) return fallback

  const parsed = Number.parseInt(value, 10)

  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback
  }

  return parsed
}

function parseFiniteNumber(
  value: string | undefined,
  fallback: number,
): number {
  if (value === undefined) return fallback

  const parsed = Number(value)

  if (!Number.isFinite(parsed)) return fallback

  return parsed
}

function failure(
  code: MemoriXServiceFailure["code"],
  error: unknown,
): MemoriXServiceFailure {
  if (error instanceof Error) {
    return {
      ok: false,
      code,
      message: error.message,
      cause: error,
    }
  }

  return {
    ok: false,
    code,
    message: String(error),
    cause: error,
  }
}

export type MemoriXRuntimeFallbacks = {
  homeDirectory?: string
  temporaryDirectory?: string
}

export function resolveDefaultMemoriXRuntimeRoot(
  environment: Pick<
    MemoriXServiceEnvironment,
    | "MEMORIX_RUNTIME_ROOT"
    | "LOCALAPPDATA"
    | "XDG_DATA_HOME"
    | "HOME"
    | "USERPROFILE"
    | "TEMP"
    | "TMP"
  > = {
    MEMORIX_RUNTIME_ROOT:
      process.env.MEMORIX_RUNTIME_ROOT,
    LOCALAPPDATA: process.env.LOCALAPPDATA,
    XDG_DATA_HOME: process.env.XDG_DATA_HOME,
    HOME: process.env.HOME,
    USERPROFILE: process.env.USERPROFILE,
    TEMP: process.env.TEMP,
    TMP: process.env.TMP,
  },
  fallbacks: MemoriXRuntimeFallbacks = {},
): string {
  const explicitRuntime =
    environment.MEMORIX_RUNTIME_ROOT?.trim()

  if (explicitRuntime) {
    return path.resolve(explicitRuntime)
  }

  const localAppData =
    environment.LOCALAPPDATA?.trim()

  if (localAppData) {
    return path.resolve(
      localAppData,
      "memoriX",
      "runtime",
    )
  }

  const xdgDataHome =
    environment.XDG_DATA_HOME?.trim()

  if (xdgDataHome) {
    return path.resolve(
      xdgDataHome,
      "memoriX",
      "runtime",
    )
  }

  const homeDirectory =
    environment.HOME?.trim() ||
    environment.USERPROFILE?.trim() ||
    fallbacks.homeDirectory?.trim() ||
    os.homedir().trim()

  if (homeDirectory) {
    return path.resolve(
      homeDirectory,
      ".local",
      "share",
      "memoriX",
      "runtime",
    )
  }

  const temporaryDirectory =
    environment.TEMP?.trim() ||
    environment.TMP?.trim() ||
    fallbacks.temporaryDirectory?.trim() ||
    os.tmpdir()

  return path.resolve(
    temporaryDirectory,
    "memoriX",
    "runtime",
  )
}

export function memoriXServiceOptionsFromEnvironment(
  environment: MemoriXServiceEnvironment = {
    MEMORIX_ENABLED: process.env.MEMORIX_ENABLED,
    MEMORIX_PYTHON_EXECUTABLE:
      process.env.MEMORIX_PYTHON_EXECUTABLE,
    MEMORIX_RUNTIME_ROOT:
      process.env.MEMORIX_RUNTIME_ROOT,
    LOCALAPPDATA: process.env.LOCALAPPDATA,
    XDG_DATA_HOME: process.env.XDG_DATA_HOME,
    HOME: process.env.HOME,
    USERPROFILE: process.env.USERPROFILE,
    TEMP: process.env.TEMP,
    TMP: process.env.TMP,
    MEMORIX_TIMEOUT_MS:
      process.env.MEMORIX_TIMEOUT_MS,
    MEMORIX_TITAN_D_MODEL:
      process.env.MEMORIX_TITAN_D_MODEL,
    MEMORIX_TITAN_HIDDEN_DIM:
      process.env.MEMORIX_TITAN_HIDDEN_DIM,
    MEMORIX_TITAN_MAX_ITEMS:
      process.env.MEMORIX_TITAN_MAX_ITEMS,
    MEMORIX_TITAN_DEVICE:
      process.env.MEMORIX_TITAN_DEVICE,
    MEMORIX_TITAN_TOP_K:
      process.env.MEMORIX_TITAN_TOP_K,
    MEMORIX_TITAN_MIN_SCORE:
      process.env.MEMORIX_TITAN_MIN_SCORE,
  },
  overrides: Partial<MemoriXServiceOptions> = {},
): MemoriXServiceOptions {
  const repositoryRoot = path.resolve(
    import.meta.dir,
    "../../../..",
  )

  const enabled =
    overrides.enabled ??
    parseBoolean(environment.MEMORIX_ENABLED, false)

  const pythonExecutable =
    overrides.pythonExecutable ??
    environment.MEMORIX_PYTHON_EXECUTABLE?.trim() ??
    ""

  const runtimeRoot =
    overrides.runtimeRoot ??
    resolveDefaultMemoriXRuntimeRoot(environment)

  return {
    enabled,
    pythonExecutable,
    projectRoot:
      overrides.projectRoot ?? repositoryRoot,
    runtimeRoot,
    timeoutMs:
      overrides.timeoutMs ??
      parsePositiveInteger(
        environment.MEMORIX_TIMEOUT_MS,
        DEFAULT_TIMEOUT_MS,
      ),
    titanDModel:
      overrides.titanDModel ??
      parsePositiveInteger(
        environment.MEMORIX_TITAN_D_MODEL,
        256,
      ),
    titanHiddenDim:
      overrides.titanHiddenDim ??
      parsePositiveInteger(
        environment.MEMORIX_TITAN_HIDDEN_DIM,
        256,
      ),
    titanMaxItems:
      overrides.titanMaxItems ??
      parsePositiveInteger(
        environment.MEMORIX_TITAN_MAX_ITEMS,
        50_000,
      ),
    titanDevice:
      overrides.titanDevice ??
      environment.MEMORIX_TITAN_DEVICE?.trim() ??
      "cpu",
    titanTopK:
      overrides.titanTopK ??
      parsePositiveInteger(
        environment.MEMORIX_TITAN_TOP_K,
        5,
      ),
    titanMinScore:
      overrides.titanMinScore ??
      parseFiniteNumber(
        environment.MEMORIX_TITAN_MIN_SCORE,
        0.12,
      ),
  }
}

export class MemoriXService {
  readonly options: MemoriXServiceOptions

  private readonly clientFactory: MemoriXClientFactory
  private client?: MemoriXClientContract
  private connecting?: Promise<MemoriXClientContract>
  private closing?: Promise<void>

  constructor(
    options: MemoriXServiceOptions,
    dependencies: MemoriXServiceDependencies = {},
  ) {
    this.options = {
      ...options,
      projectRoot: path.resolve(options.projectRoot),
      runtimeRoot: path.resolve(options.runtimeRoot),
      pythonExecutable: options.pythonExecutable
        ? path.resolve(options.pythonExecutable)
        : undefined,
    }

    this.clientFactory =
      dependencies.clientFactory ??
      ((clientOptions) => new MemoriXClient(clientOptions))
  }

  get enabled(): boolean {
    return this.options.enabled
  }

  get connected(): boolean {
    return this.client?.connected ?? false
  }

  async connect(): Promise<MemoriXServiceResult<void>> {
    try {
      await this.requireConnectedClient()

      return {
        ok: true,
        value: undefined,
      }
    } catch (error) {
      if (error instanceof MemoriXDisabledError) {
        return failure("disabled", error)
      }

      if (error instanceof MemoriXConfigurationError) {
        return failure("configuration", error)
      }

      return failure("connection", error)
    }
  }

  async status(): Promise<MemoriXServiceResult<MemoriXStatus>> {
    return this.runSafely(
      (client) => client.status(),
    )
  }

  async context(
    query: string,
    options?: {
      role?: string
      topK?: number
    },
  ): Promise<MemoriXServiceResult<MemoriXRetrievalResult>> {
    return this.runSafely(
      (client) => client.context(query, options),
    )
  }

  async searchColdHistory(
    query: string,
    options?: {
      limit?: number
    },
  ): Promise<MemoriXServiceResult<MemoriXRetrievalResult>> {
    return this.runSafely(
      (client) => client.searchColdHistory(query, options),
    )
  }

  async recordEvent(
    input: MemoriXRecordEventInput,
  ): Promise<MemoriXServiceResult<MemoriXRecordedEvent>> {
    return this.runSafely(
      (client) => client.recordEvent(input),
    )
  }

  async proposeCandidate(
    input: MemoriXProposeCandidateInput,
  ): Promise<MemoriXServiceResult<MemoriXCandidate>> {
    return this.runSafely(
      (client) => client.proposeCandidate(input),
    )
  }

  async recordProjectArchiveEntry(
    input: MemoriXProjectEntryRecordInput,
  ): Promise<MemoriXServiceResult<MemoriXProjectArchiveEntry>> {
    return this.runSafely((client) =>
      client.callTool<MemoriXProjectArchiveEntry>(
        "memorix_project_entry_record",
        input as unknown as JSONObject,
      ),
    )
  }

  async listProjectArchiveEntries(options: {
    projectID?: string | null
    entryType?: MemoriXProjectArchiveEntryType | null
  } = {}): Promise<MemoriXServiceResult<MemoriXProjectArchiveEntry[]>> {
    return this.runSafely((client) =>
      client.callTool<MemoriXProjectArchiveEntry[]>(
        "memorix_project_entries_list",
        {
          ...(options.projectID !== undefined
            ? { project_id: options.projectID }
            : {}),
          ...(options.entryType !== undefined
            ? { entry_type: options.entryType }
            : {}),
        },
      ),
    )
  }

  async rebuildProjectSnapshot(
    projectID: string,
  ): Promise<MemoriXServiceResult<MemoriXProjectSnapshot>> {
    return this.runSafely((client) =>
      client.callTool<MemoriXProjectSnapshot>(
        "memorix_project_snapshot_rebuild",
        { project_id: projectID },
      ),
    )
  }

  async getProjectSnapshot(
    projectID: string,
  ): Promise<MemoriXServiceResult<MemoriXProjectSnapshot | null>> {
    return this.runSafely((client) =>
      client.callTool<MemoriXProjectSnapshot | null>(
        "memorix_project_snapshot_get",
        { project_id: projectID },
      ),
    )
  }

  async listCandidates(
    status?: MemoriXCandidateStatus | null,
  ): Promise<MemoriXServiceResult<MemoriXCandidate[]>> {
    return this.runSafely(
      async (client) => {
        const value = await client.callTool<MemoriXCandidate[]>(
          "memorix_list_candidates",
          status ? { status } : {},
        )

        return value
      },
    )
  }

  async validateCandidate(input: {
    candidateID: string
    validatedBy: string
    validationReason: string
    finalContent?: string | null
  }): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_validate_candidate",
          {
            candidate_id: input.candidateID,
            validated_by: input.validatedBy,
            validation_reason: input.validationReason,
            ...(input.finalContent !== undefined
              ? { final_content: input.finalContent }
              : {}),
          },
        ),
    )
  }

  async rejectCandidate(input: {
    candidateID: string
    rejectedBy: string
    rejectionReason: string
  }): Promise<MemoriXServiceResult<MemoriXCandidate>> {
    return this.runSafely(
      (client) =>
        client.callTool<MemoriXCandidate>(
          "memorix_reject_candidate",
          {
            candidate_id: input.candidateID,
            rejected_by: input.rejectedBy,
            rejection_reason: input.rejectionReason,
          },
        ),
    )
  }

  async runConsolidation(
    mode = "manual",
  ): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_run_consolidation",
          { mode },
        ),
    )
  }

  async runNightly(
    clearShortTermAfterSuccess = true,
  ): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_run_nightly",
          {
            clear_short_term_after_success:
              clearShortTermAfterSuccess,
          },
        ),
    )
  }

  async capacityStatus(
    simulateActiveItems?: number,
  ): Promise<MemoriXServiceResult<JSONObject>> {
    const input: JSONObject = {}

    if (simulateActiveItems !== undefined) {
      input.simulate_active_items = simulateActiveItems
    }

    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_capacity_status",
          input,
        ),
    )
  }

  async capacityPlan(): Promise<
    MemoriXServiceResult<JSONObject>
  > {
    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_capacity_plan",
          {},
        ),
    )
  }

  async capacityPrune(input: {
    appliedBy: string
    reason: string
    maxDeactivations?: number
  }): Promise<MemoriXServiceResult<JSONObject>> {
    const arguments_: JSONObject = {
      applied_by: input.appliedBy,
      reason: input.reason,
    }

    if (input.maxDeactivations !== undefined) {
      arguments_.max_deactivations =
        input.maxDeactivations
    }

    return this.runSafely(
      (client) =>
        client.callTool<JSONObject>(
          "memorix_capacity_prune",
          arguments_,
        ),
    )
  }

  async memoryPressureStatus(
    simulateCount?: number,
    assessmentLimit = 100,
  ): Promise<MemoriXServiceResult<JSONObject>> {
    const input: JSONObject = {
      assessment_limit: assessmentLimit,
    }

    if (simulateCount !== undefined) {
      input.simulate_count = simulateCount
    }

    return this.runSafely((client) =>
      client.callTool<JSONObject>(
        "memorix_memory_pressure_status",
        input,
      ),
    )
  }

  async memoryPressureInspect(
    memoryID: string,
  ): Promise<MemoriXServiceResult<JSONObject | null>> {
    return this.runSafely((client) =>
      client.callTool<JSONObject | null>(
        "memorix_memory_pressure_inspect",
        { memory_id: memoryID },
      ),
    )
  }

  async retentionRankingStatus(
    simulateCount?: number,
    assessmentLimit = 100,
  ): Promise<MemoriXServiceResult<JSONObject>> {
    const input: JSONObject = {
      assessment_limit: assessmentLimit,
    }
    if (simulateCount !== undefined) {
      input.simulate_count = simulateCount
    }
    return this.runSafely((client) =>
      client.callTool<JSONObject>(
        "memorix_retention_ranking_status",
        input,
      ),
    )
  }

  async retentionRankingInspect(
    memoryID: string,
  ): Promise<MemoriXServiceResult<JSONObject | null>> {
    return this.runSafely((client) =>
      client.callTool<JSONObject | null>(
        "memorix_retention_ranking_inspect",
        { memory_id: memoryID },
      ),
    )
  }

  async adaptiveRoutingPlan(
    input: JSONObject,
  ): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) =>
      client.callTool<JSONObject>(
        "memorix_adaptive_routing_plan",
        input,
      ),
    )
  }

  async policySearch(input: JSONObject): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) => client.callTool<JSONObject>("memorix_policy_search", input))
  }

  async policyLifecycle(input: JSONObject): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) => client.callTool<JSONObject>("memorix_policy_lifecycle", input))
  }

  async topicBlocks(input: JSONObject): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) => client.callTool<JSONObject>("memorix_topic_blocks", input))
  }

  async consolidation(input: JSONObject): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) => client.callTool<JSONObject>("memorix_consolidation", input))
  }

  async observability(input: JSONObject): Promise<MemoriXServiceResult<JSONObject>> {
    return this.runSafely((client) => client.callTool<JSONObject>("memorix_observability", input))
  }

  async close(): Promise<void> {
    if (this.closing) {
      await this.closing
      return
    }

    const client = this.client

    this.client = undefined
    this.connecting = undefined

    if (!client) return

    this.closing = client.close()

    try {
      await this.closing
    } catch {
      // Closing memoriX must never prevent opencode shutdown.
    } finally {
      this.closing = undefined
    }
  }

  private async runSafely<T>(
    operation: (
      client: MemoriXClientContract,
    ) => Promise<T>,
  ): Promise<MemoriXServiceResult<T>> {
    try {
      const client = await this.requireConnectedClient()
      const value = await operation(client)

      return {
        ok: true,
        value,
      }
    } catch (error) {
      if (error instanceof MemoriXDisabledError) {
        return failure("disabled", error)
      }

      if (error instanceof MemoriXConfigurationError) {
        return failure("configuration", error)
      }

      if (error instanceof MemoriXClientError) {
        return failure("operation", error)
      }

      return failure("operation", error)
    }
  }

  private async requireConnectedClient(): Promise<MemoriXClientContract> {
    if (!this.enabled) {
      throw new MemoriXDisabledError()
    }

    if (!this.options.pythonExecutable?.trim()) {
      throw new MemoriXConfigurationError(
        "MEMORIX_PYTHON_EXECUTABLE is required when memoriX is enabled.",
      )
    }

    if (this.client?.connected) {
      return this.client
    }

    if (this.connecting) {
      return this.connecting
    }

    const client =
      this.client ??
      this.clientFactory({
        pythonExecutable: this.options.pythonExecutable,
        projectRoot: this.options.projectRoot,
        runtimeRoot: this.options.runtimeRoot,
        timeoutMs: this.options.timeoutMs,
        titanDModel: this.options.titanDModel,
        titanHiddenDim: this.options.titanHiddenDim,
        titanMaxItems: this.options.titanMaxItems,
        titanDevice: this.options.titanDevice,
        titanTopK: this.options.titanTopK,
        titanMinScore: this.options.titanMinScore,
      })

    this.client = client

    this.connecting = client
      .connect()
      .then(() => client)
      .catch((error) => {
        if (this.client === client) {
          this.client = undefined
        }

        throw error
      })

    try {
      return await this.connecting
    } finally {
      this.connecting = undefined
    }
  }
}

let defaultService: MemoriXService | undefined

export function getDefaultMemoriXService(): MemoriXService {
  if (!defaultService) {
    defaultService = new MemoriXService(
      memoriXServiceOptionsFromEnvironment(),
    )
  }

  return defaultService
}

export async function resetDefaultMemoriXService(): Promise<void> {
  const service = defaultService
  defaultService = undefined

  await service?.close()
}
