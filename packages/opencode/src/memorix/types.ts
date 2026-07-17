export type JSONPrimitive = string | number | boolean | null

export type JSONValue =
  | JSONPrimitive
  | JSONValue[]
  | { [key: string]: JSONValue }

export type JSONObject = {
  [key: string]: JSONValue
}

export type MemoriXToolName =
  | "memorix_record_event"
  | "memorix_context"
  | "memorix_search_cold_history"
  | "memorix_propose_candidate"
  | "memorix_list_candidates"
  | "memorix_validate_candidate"
  | "memorix_reject_candidate"
  | "memorix_forget_memory"
  | "memorix_run_consolidation"
  | "memorix_run_nightly"
  | "memorix_project_entry_record"
  | "memorix_project_entries_list"
  | "memorix_project_snapshot_rebuild"
  | "memorix_project_snapshot_get"
  | "memorix_capacity_status"
  | "memorix_capacity_plan"
  | "memorix_capacity_prune"
  | "memorix_status"

export type MemoriXToolDefinition = {
  name: string
  description?: string
  inputSchema: JSONObject
}

export type MemoriXToolCallResult = {
  content?: Array<{
    type: string
    text?: string
  }>
  structuredContent?: JSONObject
  isError?: boolean
}

export type MemoriXStatus = {
  architecture: string
  retrieval_contract: string
  cold_site_contract: string
  automatic_rehydration: boolean
  short_term_events: number
  cold_archive_events: number
  project_archive_entries: number
  project_archive_snapshots: number
  hot_memories_total: number
  hot_memories_active: number
  candidates: {
    pending: number
    validated: number
    rejected: number
  }
  paths: JSONObject
  titan: JSONObject
}

export type MemoriXRetrievalMatch = {
  memory_id: string
  content: string
  score: number
  metadata: JSONObject
}

export type MemoriXRetrievalResult = {
  query: string
  source: "hot_site" | "cold_audit"
  matches: MemoriXRetrievalMatch[]
}

export type MemoriXRecordEventInput = {
  content: string
  event_type: string
  source: string
  project_id?: string | null
  session_id?: string | null
  importance?: number
  confidence?: number
  surprise?: number
  metadata?: JSONObject
}

export type MemoriXClientOptions = {
  /**
   * Absolute path to the Python executable.
   *
   * On Windows, do not rely on the Microsoft Store `python` alias.
   */
  pythonExecutable: string

  /**
   * Absolute repository root containing scripts/memorix_mcp_server.py.
   */
  projectRoot: string

  /**
   * Runtime directory used by the Python memory.
   */
  runtimeRoot: string

  timeoutMs?: number
  titanDModel?: number
  titanHiddenDim?: number
  titanMaxItems?: number
  titanDevice?: string
  titanTopK?: number
  titanMinScore?: number
}
export type MemoriXServiceErrorCode =
  | "disabled"
  | "configuration"
  | "connection"
  | "operation"

export type MemoriXServiceFailure = {
  ok: false
  code: MemoriXServiceErrorCode
  message: string
  cause?: unknown
}

export type MemoriXServiceSuccess<T> = {
  ok: true
  value: T
}

export type MemoriXServiceResult<T> =
  | MemoriXServiceSuccess<T>
  | MemoriXServiceFailure

export type MemoriXServiceOptions = {
  enabled: boolean
  pythonExecutable?: string
  projectRoot: string
  runtimeRoot: string
  timeoutMs?: number
  titanDModel?: number
  titanHiddenDim?: number
  titanMaxItems?: number
  titanDevice?: string
  titanTopK?: number
  titanMinScore?: number
}

export type MemoriXServiceEnvironment = {
  MEMORIX_ENABLED?: string
  MEMORIX_PYTHON_EXECUTABLE?: string
  MEMORIX_RUNTIME_ROOT?: string
  LOCALAPPDATA?: string
  XDG_DATA_HOME?: string
  HOME?: string
  USERPROFILE?: string
  TEMP?: string
  TMP?: string
  MEMORIX_TIMEOUT_MS?: string
  MEMORIX_TITAN_D_MODEL?: string
  MEMORIX_TITAN_HIDDEN_DIM?: string
  MEMORIX_TITAN_MAX_ITEMS?: string
  MEMORIX_TITAN_DEVICE?: string
  MEMORIX_TITAN_TOP_K?: string
  MEMORIX_TITAN_MIN_SCORE?: string
}
export type MemoriXStoredEvent = {
  event_id: string
  content: string
  event_type: string
  source: string
  created_at: string
  project_id: string | null
  session_id: string | null
  importance: number
  confidence: number
  surprise: number
  metadata: JSONObject
}

export type MemoriXArchivedEvent = {
  event_id: string
  content: string
  event_type: string
  source: string
  original_created_at: string
  archived_at: string
  project_id: string | null
  session_id: string | null
  metadata: JSONObject
}

export type MemoriXRecordedEvent = {
  short_term_event: MemoriXStoredEvent
  archived_event: MemoriXArchivedEvent
}

export type MemoriXCandidateStatus =
  | "pending"
  | "validated"
  | "rejected"

export type MemoriXCandidate = {
  candidate_id: string
  content: string
  reason: string
  source_event_ids: string[]
  created_at: string
  status: MemoriXCandidateStatus
  importance: number
  confidence: number
  surprise: number
  target_memory_id: string | null
  metadata: JSONObject
}

export type MemoriXProposeCandidateInput = {
  content: string
  reason: string
  source_event_ids: string[]
  importance?: number
  confidence?: number
  surprise?: number
  target_memory_id?: string | null
  metadata?: JSONObject
}
export type MemoriXHookOptions = {
  captureUserMessages: boolean
  captureToolResults: boolean
  maxMessageCharacters: number
  maxToolOutputCharacters: number
  ignoredTools: readonly string[]
}

export type MemoriXHookEnvironment = {
  MEMORIX_HOOK_CAPTURE_MESSAGES?: string
  MEMORIX_HOOK_CAPTURE_TOOL_RESULTS?: string
  MEMORIX_HOOK_MAX_MESSAGE_CHARACTERS?: string
  MEMORIX_HOOK_MAX_TOOL_OUTPUT_CHARACTERS?: string
  MEMORIX_HOOK_IGNORED_TOOLS?: string
}

export type MemoriXHookOutcome =
  | {
      status: "recorded"
      eventID: string
    }
  | {
      status: "skipped"
      reason: string
    }
  | {
      status: "unavailable"
      reason: string
    }

export type MemoriXProjectArchiveEntryType =
  | "identity"
  | "objective"
  | "decision"
  | "architecture"
  | "milestone"
  | "task_completed"
  | "task_remaining"
  | "problem"
  | "solution"
  | "change"
  | "note"

export type MemoriXProjectArchiveEntry = {
  entry_id: string
  project_id: string
  entry_type: MemoriXProjectArchiveEntryType
  title: string
  content: string
  source_event_ids: string[]
  author: string
  created_at: string
  recorded_at: string
  metadata: JSONObject
}

export type MemoriXProjectSnapshot = {
  project_id: string
  name: string
  summary: string
  objectives: string[]
  decisions: string[]
  architecture: string[]
  milestones: string[]
  completed_tasks: string[]
  remaining_tasks: string[]
  problems: string[]
  solutions: string[]
  latest_changes: string[]
  source_entry_ids: string[]
  version: number
  updated_at: string
}

export type MemoriXProjectEntryRecordInput = {
  project_id: string
  entry_type: MemoriXProjectArchiveEntryType
  title: string
  content: string
  source_event_ids: string[]
  author: string
  metadata?: JSONObject
}
