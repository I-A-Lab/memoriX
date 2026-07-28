import type { MemoriXService } from "./service"
import type {
  JSONObject,
  MemoriXRetrievalMatch,
  MemoriXServiceFailure,
} from "./types"

export interface MemoryFact {
  id: string
  subject: string
  content: string
  tags: readonly string[]
  timestamp: number
}

export type MemoryFacadeContext = {
  sessionID: string
  messageID: string
  agent: string
  projectID?: string | null
  userID?: string | null
}

export type MemoryStoreFacadeInput = {
  subject: string
  content: string
  tags: readonly string[]
}

export type MemoryRetrieveFacadeInput = {
  query: string
  tags?: readonly string[]
  projectID?: string | null
  userID?: string | null
}

export type MemoryStoreStatus =
  | "pending_review"
  | "archived_only"
  | "unavailable"

export type MemoryStoreFacadeMetadata = {
  status: MemoryStoreStatus
  fact?: MemoryFact
  eventID?: string
  candidateID?: string
  failure?: {
    code: string
    message: string
  }
}

export type MemoryRetrieveFacadeMetadata = {
  source: "hot_site"
  results: MemoryFact[]
  failure?: {
    code: string
    message: string
  }
}

export type MemoryFacadeResult<M> = {
  title: string
  output: string
  metadata: M
}

export type MemoryFacadeService = Pick<
  MemoriXService,
  | "recordEvent"
  | "proposeCandidate"
  | "context"
>

function normalizedText(
  value: string,
): string {
  return value.trim()
}

function normalizeTags(
  tags: readonly string[],
): string[] {
  return [
    ...new Set(
      tags
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0),
    ),
  ]
}

function canonicalMemoryContent(
  input: MemoryStoreFacadeInput,
  tags: readonly string[],
): string {
  const lines = [
    `Subject: ${normalizedText(input.subject)}`,
    `Content: ${normalizedText(input.content)}`,
  ]

  if (tags.length > 0) {
    lines.push(`Tags: ${tags.join(", ")}`)
  }

  return lines.join("\n")
}

function serviceFailure(
  failure: MemoriXServiceFailure,
): {
  code: string
  message: string
} {
  return {
    code: failure.code,
    message: failure.message,
  }
}

function metadataString(
  metadata: JSONObject,
  key: string,
): string | undefined {
  const value = metadata[key]

  return typeof value === "string" &&
    value.trim().length > 0
    ? value
    : undefined
}

function metadataTags(
  metadata: JSONObject,
): string[] {
  const value = metadata.tags

  if (!Array.isArray(value)) return []

  return value.filter(
    (tag): tag is string =>
      typeof tag === "string" &&
      tag.trim().length > 0,
  )
}

function timestampFromMetadata(
  metadata: JSONObject,
): number {
  const raw =
    metadataString(metadata, "validated_at") ??
    metadataString(metadata, "created_at")

  if (!raw) return 0

  const parsed = Date.parse(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

function matchToFact(
  match: MemoriXRetrievalMatch,
): MemoryFact {
  const subject =
    metadataString(match.metadata, "subject") ??
    "memoriX memory"

  const originalContent =
    metadataString(
      match.metadata,
      "original_content",
    ) ?? match.content

  return {
    id: match.memory_id,
    subject,
    content: originalContent,
    tags: metadataTags(match.metadata),
    timestamp: timestampFromMetadata(
      match.metadata,
    ),
  }
}

function tagsMatch(
  fact: MemoryFact,
  requiredTags: readonly string[],
): boolean {
  if (requiredTags.length === 0) return true

  const factTags = new Set(
    fact.tags.map((tag) => tag.toLowerCase()),
  )

  return requiredTags.some(
    (tag) => factTags.has(tag.toLowerCase()),
  )
}

export async function storeMemoryThroughMemoriX(
  service: MemoryFacadeService,
  input: MemoryStoreFacadeInput,
  context: MemoryFacadeContext,
): Promise<
  MemoryFacadeResult<MemoryStoreFacadeMetadata>
> {
  const subject = normalizedText(input.subject)
  const content = normalizedText(input.content)
  const tags = normalizeTags(input.tags)

  if (!subject || !content) {
    return {
      title: "Memory was not stored",
      output:
        "memory_store requires a non-empty subject and content.",
      metadata: {
        status: "unavailable",
        failure: {
          code: "invalid_input",
          message:
            "subject and content must not be empty",
        },
      },
    }
  }

  const canonicalContent =
    canonicalMemoryContent(input, tags)

  const recorded = await service.recordEvent({
    content: canonicalContent,
    event_type: "opencode_memory_fact",
    source: "opencode.memory_store",
    project_id: context.projectID,
    session_id: context.sessionID,
    importance: 0.9,
    confidence: 1,
    surprise: 0.5,
    metadata: {
      subject,
      original_content: content,
      tags,
      source_tool: "memory_store",
      opencode_agent: context.agent,
      opencode_message_id: context.messageID,
      opencode_session_id: context.sessionID,
      ...(context.projectID !== undefined
        ? { project_id: context.projectID }
        : {}),
      ...(context.userID !== undefined
        ? { user_id: context.userID }
        : {}),
    },
  })

  if (!recorded.ok) {
    return {
      title: "memoriX unavailable",
      output:
        `The memory could not be recorded: ${recorded.message}`,
      metadata: {
        status: "unavailable",
        failure: serviceFailure(recorded),
      },
    }
  }

  const event =
    recorded.value.short_term_event

  const createdTimestamp =
    Date.parse(event.created_at)

  const fact: MemoryFact = {
    id: event.event_id,
    subject,
    content,
    tags,
    timestamp: Number.isFinite(
      createdTimestamp,
    )
      ? createdTimestamp
      : 0,
  }

  const candidate =
    await service.proposeCandidate({
      content: canonicalContent,
      reason:
        "Explicit memory_store request from opencode; human validation is required before Titan hot-site storage.",
      source_event_ids: [
        event.event_id,
      ],
      importance: 0.9,
      confidence: 1,
      surprise: 0.5,
      metadata: {
        subject,
        original_content: content,
        tags,
        source_tool: "memory_store",
        source_event_id: event.event_id,
        opencode_agent: context.agent,
        opencode_message_id:
          context.messageID,
        opencode_session_id:
          context.sessionID,
        ...(context.projectID !== undefined
          ? { project_id: context.projectID }
          : {}),
        ...(context.userID !== undefined
          ? { user_id: context.userID }
          : {}),
      },
    })

  if (!candidate.ok) {
    return {
      title:
        `Archived memory event: ${subject}`,
      output:
        "The fact was written to short-term memory and the cold archive, " +
        "but creation of the pending hot-site candidate failed. " +
        `Reason: ${candidate.message}`,
      metadata: {
        status: "archived_only",
        fact,
        eventID: event.event_id,
        failure: serviceFailure(candidate),
      },
    }
  }

  return {
    title:
      `Memory awaiting review: ${subject}`,
    output:
      "The fact was archived in short-term and cold history. " +
      `Pending candidate ${candidate.value.candidate_id} was created. ` +
      "It will not be available through memory_retrieve until a human validates it.",
    metadata: {
      status: "pending_review",
      fact,
      eventID: event.event_id,
      candidateID:
        candidate.value.candidate_id,
    },
  }
}

export async function retrieveMemoryThroughMemoriX(
  service: MemoryFacadeService,
  input: MemoryRetrieveFacadeInput,
): Promise<
  MemoryFacadeResult<MemoryRetrieveFacadeMetadata>
> {
  const query = normalizedText(input.query)
  const requestedTags = normalizeTags(
    input.tags ?? [],
  )

  if (!query) {
    return {
      title: "No memory query provided",
      output:
        "memory_retrieve requires a non-empty query.",
      metadata: {
        source: "hot_site",
        results: [],
        failure: {
          code: "invalid_input",
          message: "query must not be empty",
        },
      },
    }
  }

  const retrievalQuery = [
    query,
    ...requestedTags,
  ].join(" ")

  const retrieval = await service.context(
    retrievalQuery,
    {
      topK: requestedTags.length > 0
        ? 20
        : 10,
      projectID: input.projectID,
      userID: input.userID,
    },
  )

  if (!retrieval.ok) {
    return {
      title: "memoriX unavailable",
      output:
        `Validated hot-site memory could not be retrieved: ${retrieval.message}`,
      metadata: {
        source: "hot_site",
        results: [],
        failure: serviceFailure(retrieval),
      },
    }
  }

  if (retrieval.value.source !== "hot_site") {
    return {
      title: "memoriX contract violation",
      output:
        "memory_retrieve refused a result that did not originate from the Titan hot site.",
      metadata: {
        source: "hot_site",
        results: [],
        failure: {
          code: "contract_violation",
          message:
            "memory_retrieve accepts hot_site results only",
        },
      },
    }
  }

  const results = retrieval.value.matches
    .map(matchToFact)
    .filter(
      (fact) =>
        tagsMatch(fact, requestedTags),
    )

  return {
    title:
      `Retrieved ${results.length} validated memory facts`,
    output:
      results.length > 0
        ? JSON.stringify(results, null, 2)
        : "No matching validated hot-site memory facts were found.",
    metadata: {
      source: "hot_site",
      results,
    },
  }
}
