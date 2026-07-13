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
