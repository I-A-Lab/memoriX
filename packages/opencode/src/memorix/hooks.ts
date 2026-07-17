import type {
  MemoriXHookEnvironment,
  MemoriXHookOptions,
  MemoriXHookOutcome,
  MemoriXRecordedEvent,
  MemoriXServiceResult,
} from "./types"

const DEFAULT_MAX_MESSAGE_CHARACTERS = 12_000
const DEFAULT_MAX_TOOL_OUTPUT_CHARACTERS = 16_000

const DEFAULT_IGNORED_TOOLS = [
  "memory_store",
  "memory_retrieve",
  "memory_candidates_list",
  "memory_candidate_validate",
  "memory_candidate_reject",
  "memory_consolidate",
  "memory_nightly_run",
  "memory_capacity_status",
  "memory_capacity_plan",
  "memory_capacity_prune",
  "memory_status",
  "project_archive_record",
  "project_archive_list",
  "project_snapshot_rebuild",
  "project_snapshot_get",
]

export type MemoriXHookService = {
  recordEvent(input: {
    content: string
    event_type: string
    source: string
    project_id?: string | null
    session_id?: string | null
    importance?: number
    confidence?: number
    surprise?: number
    metadata?: Record<string, unknown>
  }): Promise<
    MemoriXServiceResult<MemoriXRecordedEvent>
  >
}

export type MemoriXUserMessageHookInput = {
  sessionID: string
  messageID?: string
  agent?: string
  model?: {
    providerID: string
    modelID: string
  }
  variant?: string
  text: string
}

export type MemoriXToolResultHookInput = {
  sessionID: string
  callID: string
  tool: string
  agent?: string
  args: unknown
  title: string
  output: string
  metadata: unknown
}

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
  if (!value) return fallback

  const parsed = Number.parseInt(value, 10)

  return Number.isFinite(parsed) && parsed > 0
    ? parsed
    : fallback
}

function parseIgnoredTools(
  value: string | undefined,
): string[] {
  const customIgnoredTools = value
    ?.split(",")
    .map((tool) => tool.trim().toLowerCase())
    .filter(Boolean) ?? []

  return [
    ...new Set([
      ...DEFAULT_IGNORED_TOOLS,
      ...customIgnoredTools,
    ]),
  ]
}

export function memoriXHookOptionsFromEnvironment(
  environment: MemoriXHookEnvironment = {
    MEMORIX_HOOK_CAPTURE_MESSAGES:
      process.env.MEMORIX_HOOK_CAPTURE_MESSAGES,
    MEMORIX_HOOK_CAPTURE_TOOL_RESULTS:
      process.env.MEMORIX_HOOK_CAPTURE_TOOL_RESULTS,
    MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS:
      process.env.MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS,
    MEMORIX_HOOK_MAX_TOOL_OUTPUT_CHARACTERS:
      process.env.MEMORIX_HOOK_MAX_TOOL_OUTPUT_CHARACTERS,
    MEMORIX_HOOK_IGNORED_TOOLS:
      process.env.MEMORIX_HOOK_IGNORED_TOOLS,
  },
): MemoriXHookOptions {
  return {
    captureUserMessages: parseBoolean(
      environment.MEMORIX_HOOK_CAPTURE_MESSAGES,
      false,
    ),
    captureToolResults: parseBoolean(
      environment.MEMORIX_HOOK_CAPTURE_TOOL_RESULTS,
      false,
    ),
    maxMessageCharacters: parsePositiveInteger(
      environment.MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS,
      DEFAULT_MAX_MESSAGE_CHARACTERS,
    ),
    maxToolOutputCharacters: parsePositiveInteger(
      environment.MEMORIX_HOOK_MAX_TOOL_OUTPUT_CHARACTERS,
      DEFAULT_MAX_TOOL_OUTPUT_CHARACTERS,
    ),
    ignoredTools: parseIgnoredTools(
      environment.MEMORIX_HOOK_IGNORED_TOOLS,
    ),
  }
}

function truncateText(
  value: string,
  maximum: number,
): {
  value: string
  truncated: boolean
  originalLength: number
} {
  const normalized = value.trim()
  const originalLength = normalized.length

  if (originalLength <= maximum) {
    return {
      value: normalized,
      truncated: false,
      originalLength,
    }
  }

  return {
    value:
      normalized.slice(0, maximum) +
      "\n[truncated by memoriX hook]",
    truncated: true,
    originalLength,
  }
}

function safeJSON(value: unknown): unknown {
  try {
    return JSON.parse(JSON.stringify(value))
  } catch {
    return {
      serialization_error:
        "Value could not be serialized safely.",
    }
  }
}

function outcomeFromRecord(
  result: MemoriXServiceResult<MemoriXRecordedEvent>,
): MemoriXHookOutcome {
  if (!result.ok) {
    return {
      status: "unavailable",
      reason: result.message,
    }
  }

  return {
    status: "recorded",
    eventID:
      result.value.short_term_event.event_id,
  }
}

export async function recordUserMessageHook(
  service: MemoriXHookService,
  options: MemoriXHookOptions,
  input: MemoriXUserMessageHookInput,
): Promise<MemoriXHookOutcome> {
  if (!options.captureUserMessages) {
    return {
      status: "skipped",
      reason:
        "User-message capture is disabled.",
    }
  }

  const captured = truncateText(
    input.text,
    options.maxMessageCharacters,
  )

  if (!captured.value) {
    return {
      status: "skipped",
      reason:
        "The user message contained no text.",
    }
  }

  const result = await service.recordEvent({
    content: captured.value,
    event_type: "opencode_user_message",
    source: "opencode.hook.chat.message",
    session_id: input.sessionID,
    importance: 0.4,
    confidence: 1,
    surprise: 0,
    metadata: {
      source_hook: "chat.message",
      opencode_session_id: input.sessionID,
      opencode_message_id:
        input.messageID ?? null,
      opencode_agent:
        input.agent ?? null,
      opencode_variant:
        input.variant ?? null,
      opencode_model_provider:
        input.model?.providerID ?? null,
      opencode_model_id:
        input.model?.modelID ?? null,
      truncated: captured.truncated,
      original_length:
        captured.originalLength,
    },
  })

  return outcomeFromRecord(result)
}

export async function recordToolResultHook(
  service: MemoriXHookService,
  options: MemoriXHookOptions,
  input: MemoriXToolResultHookInput,
): Promise<MemoriXHookOutcome> {
  if (!options.captureToolResults) {
    return {
      status: "skipped",
      reason:
        "Tool-result capture is disabled.",
    }
  }

  if (options.ignoredTools.includes(input.tool)) {
    return {
      status: "skipped",
      reason:
        `Tool is excluded from capture: ${input.tool}`,
    }
  }

  const captured = truncateText(
    input.output,
    options.maxToolOutputCharacters,
  )

  if (!captured.value) {
    return {
      status: "skipped",
      reason:
        "The tool result contained no output.",
    }
  }

  const content = [
    `Tool: ${input.tool}`,
    `Title: ${input.title}`,
    "",
    captured.value,
  ].join("\n")

  const result = await service.recordEvent({
    content,
    event_type: "opencode_tool_result",
    source:
      "opencode.hook.tool.execute.after",
    session_id: input.sessionID,
    importance: 0.35,
    confidence: 1,
    surprise: 0,
    metadata: {
      source_hook:
        "tool.execute.after",
      opencode_session_id:
        input.sessionID,
      opencode_call_id: input.callID,
      opencode_agent:
        input.agent ?? null,
      tool: input.tool,
      tool_title: input.title,
      tool_args: safeJSON(input.args),
      tool_metadata:
        safeJSON(input.metadata),
      truncated: captured.truncated,
      original_length:
        captured.originalLength,
    },
  })

  return outcomeFromRecord(result)
}
